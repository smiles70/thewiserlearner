"""Visual provider abstraction and local renderer.

The pipeline gets per-beat background imagery from a `VisualProvider`. Two
implementations live in this codebase:

  - `LocalProvider` (this module) — deterministic, offline, no network. Renders
    calm gradient cards from the palette declared in `visual_theme`. Used as
    the default and as an unconditional fallback when a remote provider fails.
  - `FalProvider` (`pipeline.providers.fal`, optional) — talks to fal.ai's
    image-generation API. Lives behind the same Protocol so the compositor
    never has to know which backend produced an image.

Public surface:

    class VisualProvider(Protocol): ...
    class LocalProvider: ...
    def generate_all(composition, out_dir, provider) -> dict[str, Path]
    def palette_to_colors(name: str) -> tuple[RGB, RGB]

Contract clauses honoured at this layer:

  - C-6.1   PNGs are 1920x1080 (final mp4 frame size)
  - C-6.4   palette never relies on blue/yellow alone for meaning
  - C-6.5   no animation here; motion is added by the compositor (Ken Burns
            + xfade) within the contract's 400-800 ms transition window
  - C-6.9   pilots are faceless; LocalProvider produces no faces by
            construction; FalProvider must enforce this in prompts
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from pipeline.storyboard import BeatComposition, Composition, VisualTheme

# --------------------------------------------------------------------------- #
# Constants                                                                   #
# --------------------------------------------------------------------------- #

CARD_WIDTH = 1920
CARD_HEIGHT = 1080

RGB = tuple[int, int, int]

# Palette table. Each entry is (top_color, bottom_color) for a vertical gradient.
# Keys mirror visual_theme.palette names from the visual-director skill.
# All foreground text the compositor overlays is white (245,247,250); the
# luminance of every entry below has been chosen so contrast against that
# foreground exceeds 7:1 (C-6.3).
_PALETTES: dict[str, tuple[RGB, RGB]] = {
    "warm-neutral-morning-light": ((28, 32, 38), (18, 22, 28)),
    "warm-neutral-evening-lamp": ((34, 28, 26), (20, 17, 16)),
    "cool-neutral-overcast": ((30, 34, 40), (18, 22, 28)),
    "muted-sage-quiet": ((24, 32, 28), (16, 22, 20)),
    "muted-clay-quiet": ((36, 28, 26), (22, 18, 16)),
}

DEFAULT_PALETTE: tuple[RGB, RGB] = _PALETTES["warm-neutral-morning-light"]


def palette_to_colors(name: str) -> tuple[RGB, RGB]:
    """Resolve a palette name to (top_rgb, bottom_rgb). Unknown names fall
    back to the morning-light default — never raise. The visual-director
    skill is free to invent palette names; the LocalProvider degrades
    gracefully rather than crashing the pipeline."""
    return _PALETTES.get(name, DEFAULT_PALETTE)


# --------------------------------------------------------------------------- #
# Provider interface                                                          #
# --------------------------------------------------------------------------- #


@dataclass
class VisualResult:
    """One generated background image."""

    beat_name: str
    image_path: Path
    width: int
    height: int


class VisualProvider(Protocol):
    """Anything that can render a 1920x1080 background image for a beat.

    Implementations must be **idempotent** when given the same `out_path`:
    callers may re-run the pipeline and expect existing images to be reused
    or overwritten without error. Implementations must never produce a file
    smaller than 16 KB (a heuristic for "ffmpeg-readable PNG").
    """

    def generate(
        self,
        beat: BeatComposition,
        theme: VisualTheme,
        out_path: Path,
    ) -> Path:  # pragma: no cover - Protocol body
        ...


# --------------------------------------------------------------------------- #
# Local (offline) provider                                                    #
# --------------------------------------------------------------------------- #


class LocalProvider:
    """Render a calm gradient card from the theme palette, no network.

    The image is intentionally simple: a vertical gradient with a single
    very-soft decorative orb. All meaning lives in (a) the spoken audio,
    (b) the captions, and (c) the title/step overlays the compositor draws
    on top. This satisfies C-6.7 (no novel icon vocabularies) and C-6.4
    (colour is never the sole carrier of meaning).
    """

    def __init__(self, *, width: int = CARD_WIDTH, height: int = CARD_HEIGHT) -> None:
        self.width = width
        self.height = height

    def generate(
        self,
        beat: BeatComposition,
        theme: VisualTheme,
        out_path: Path,
    ) -> Path:
        from PIL import Image, ImageDraw, ImageFilter

        top, bottom = palette_to_colors(theme.palette)
        img = Image.new("RGB", (self.width, self.height), bottom)
        # Vertical gradient, top -> bottom.
        for y in range(self.height):
            t = y / max(1, self.height - 1)
            r = int(top[0] + (bottom[0] - top[0]) * t)
            g = int(top[1] + (bottom[1] - top[1]) * t)
            b = int(top[2] + (bottom[2] - top[2]) * t)
            ImageDraw.Draw(img).line([(0, y), (self.width, y)], fill=(r, g, b))

        # Subtle decorative orb. Beat-name hash drives position so each beat
        # looks slightly different without any randomness — the pipeline
        # stays reproducible.
        h = sum(ord(c) for c in beat.beat)
        orb_x = int(self.width * (0.20 + 0.55 * ((h * 37) % 100) / 100.0))
        orb_y = int(self.height * (0.30 + 0.40 * ((h * 53) % 100) / 100.0))
        orb_radius = int(self.height * 0.45)

        orb = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(orb).ellipse(
            [
                (orb_x - orb_radius, orb_y - orb_radius),
                (orb_x + orb_radius, orb_y + orb_radius),
            ],
            fill=(top[0] + 18, top[1] + 14, top[2] + 10, 38),
        )
        orb = orb.filter(ImageFilter.GaussianBlur(radius=80))
        img = Image.alpha_composite(img.convert("RGBA"), orb).convert("RGB")

        out_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(out_path, "PNG", optimize=True)
        return out_path


# --------------------------------------------------------------------------- #
# Orchestration                                                               #
# --------------------------------------------------------------------------- #


def generate_all(
    composition: Composition,
    out_dir: Path,
    provider: VisualProvider | None = None,
) -> dict[str, VisualResult]:
    """Render one card per beat. Returns a dict keyed by beat name.

    The provider may be omitted; the LocalProvider is the default.
    Per-beat output paths live at ``out_dir / "visuals" / "<beat>.png"``.
    """
    provider = provider or LocalProvider()
    visuals_dir = out_dir / "visuals"
    visuals_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, VisualResult] = {}
    for beat in composition.beats:
        path = visuals_dir / f"{beat.beat}.png"
        provider.generate(beat, composition.visual_theme, path)
        # Record what was produced. We re-read the file size to surface a
        # silent-failure mode (provider claimed success but wrote 0 bytes).
        if not path.is_file() or path.stat().st_size < 16 * 1024:
            raise RuntimeError(f"visual provider produced an unusably small file at {path}")
        results[beat.beat] = VisualResult(
            beat_name=beat.beat,
            image_path=path,
            width=CARD_WIDTH,
            height=CARD_HEIGHT,
        )
    return results
