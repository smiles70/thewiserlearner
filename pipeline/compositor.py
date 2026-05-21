"""Video composition (FFmpeg).

v0.1 minimum-viable visual: one title card (rendered with Pillow) shown for
the full episode duration, with the voice audio and burned-in captions.

This is a defensible MVP for an older-adult audience: voice and captions are
the primary information channels (C-7.* and C-5.*); the image is attribution.
A future v0.2 swaps in per-beat cards and b-roll using the visual-director
agent's `composition.yaml`.

Public API:
    composite(voice_path, captions_srt, script_path, out_dir) -> CompositeResult

Contract clauses honoured at v0.1:
  - C-6.1 1920x1080 16:9
  - C-6.2 typography (heading >= 72 px; body >= 48 px)
  - C-6.3 contrast >= 7:1 (white on near-black)
  - C-6.5 no rapid motion (the card is static)
  - C-7.1 captions burned in
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from pipeline.audit import parse_script

VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
VIDEO_FPS = 25

BACKGROUND_RGB = (18, 22, 28)  # near-black; contrast vs white = 16.9:1
FOREGROUND_RGB = (245, 247, 250)
ACCENT_RGB = (140, 180, 220)

TITLE_FONT_PX = 88  # >= contract heading minimum 72
SUBTITLE_FONT_PX = 56  # >= contract body minimum 48

TITLE_TOP_PCT = 0.32  # y position as fraction of frame height
SUBTITLE_TOP_PCT = 0.55


@dataclass
class CompositeResult:
    video_path: Path
    duration_seconds: float


# --------------------------------------------------------------------------- #
# Card rendering                                                              #
# --------------------------------------------------------------------------- #


def _resolve_font(size_px: int):
    """Locate a usable TrueType font; fall back to Pillow's default bitmap."""
    from PIL import ImageFont

    candidates = [
        # Common Windows fonts
        "C:/Windows/Fonts/segoeuib.ttf",  # Segoe UI Bold
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        # Common macOS fonts
        "/System/Library/Fonts/SFNS.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        # Common Linux fonts (DejaVu ships in most distros)
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    ]
    for path in candidates:
        if Path(path).is_file():
            try:
                return ImageFont.truetype(path, size=size_px)
            except OSError:  # pragma: no cover - font ABI quirk
                continue
    return ImageFont.load_default()


def _wrap_words(text: str, font, draw, max_width_px: int) -> list[str]:
    """Greedy word-wrap that respects ``max_width_px`` for the given font."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for w in words:
        candidate = f"{current} {w}".strip()
        if draw.textlength(candidate, font=font) <= max_width_px:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines


def render_title_card(
    title: str,
    subtitle: str,
    out_path: Path,
    *,
    width: int = VIDEO_WIDTH,
    height: int = VIDEO_HEIGHT,
) -> Path:
    """Render a 16:9 title card PNG. Returns the output path."""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (width, height), BACKGROUND_RGB)
    draw = ImageDraw.Draw(img)

    title_font = _resolve_font(TITLE_FONT_PX)
    subtitle_font = _resolve_font(SUBTITLE_FONT_PX)

    margin = int(width * 0.08)
    text_max = width - 2 * margin

    title_lines = _wrap_words(title, title_font, draw, text_max)
    subtitle_lines = _wrap_words(subtitle, subtitle_font, draw, text_max)

    y = int(height * TITLE_TOP_PCT)
    for line in title_lines:
        line_w = draw.textlength(line, font=title_font)
        draw.text(((width - line_w) / 2, y), line, fill=FOREGROUND_RGB, font=title_font)
        y += int(TITLE_FONT_PX * 1.25)

    y = int(height * SUBTITLE_TOP_PCT)
    for line in subtitle_lines:
        line_w = draw.textlength(line, font=subtitle_font)
        draw.text(((width - line_w) / 2, y), line, fill=ACCENT_RGB, font=subtitle_font)
        y += int(SUBTITLE_FONT_PX * 1.3)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG")
    return out_path


# --------------------------------------------------------------------------- #
# Public entry point                                                          #
# --------------------------------------------------------------------------- #


def composite(
    voice_path: Path,
    captions_srt: Path | None,
    script_path: Path,
    out_dir: Path,
) -> CompositeResult:
    """Render an MP4 from voice + (optional) captions + a generated title card.

    Requires ``ffmpeg`` and ``ffprobe`` on PATH.
    """
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise RuntimeError("ffmpeg and ffprobe must be on PATH")
    if not voice_path.is_file():
        raise FileNotFoundError(voice_path)

    fm, _ = parse_script(script_path)
    title = str(fm.get("title") or fm.get("id") or "")
    subtitle = "The Wiser Learner"

    out_dir.mkdir(parents=True, exist_ok=True)
    card_path = out_dir / "title_card.png"
    render_title_card(title, subtitle, card_path)

    final_mp4 = out_dir / "episode.mp4"
    cmd = build_ffmpeg_command(card_path, voice_path, captions_srt, final_mp4)
    subprocess.run(cmd, check=True)

    duration = _audio_duration(final_mp4)
    return CompositeResult(video_path=final_mp4, duration_seconds=duration)


def build_ffmpeg_command(
    card_path: Path,
    voice_path: Path,
    captions_srt: Path | None,
    out_path: Path,
) -> list[str]:
    """Build the ffmpeg command line. Pure: easy to unit-test."""
    cmd: list[str] = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-loop",
        "1",
        "-framerate",
        str(VIDEO_FPS),
        "-i",
        str(card_path),
        "-i",
        str(voice_path),
    ]
    if captions_srt is not None:
        srt_arg = str(captions_srt).replace("\\", "/").replace(":", r"\:")
        cmd.extend(
            [
                "-vf",
                (
                    f"subtitles='{srt_arg}':force_style="
                    "'Fontname=Arial,Fontsize=22,PrimaryColour=&H00FFFFFF,"
                    "BackColour=&HB2000000,BorderStyle=4,Outline=0,Shadow=0,"
                    "Alignment=2,MarginV=70'"
                ),
            ]
        )
    cmd.extend(
        [
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(out_path),
        ]
    )
    return cmd


def _audio_duration(path: Path) -> float:
    out = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(out.stdout.strip())
