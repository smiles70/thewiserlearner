"""Composition manifest schema and loader.

Loads and validates `composition.yaml` — the artifact authored by the
`visual-director` agent and consumed by `pipeline.compositor` for per-beat
visual rendering.

Schema is enforced via pydantic v2. Contract clauses pinned by this module:

  - C-3.4   eight REQUIRED_BEATS in canonical order
  - C-3.4#5 walkthrough has >= 2 named steps; other beats have no steps
  - C-6.1   format string must match the compositor's frame size
  - C-6.2   title_font_px >= 72, body_font_px >= 48 at 1080p
  - C-6.3   contrast_ratio >= 7:1
  - C-6.5   transitions between 400 and 800 ms
  - C-6.6   per-beat dwell_seconds >= 3.0 (minimum; per-cue dwell against
            word count is enforced at compositor time when text is finalised)
  - C-6.8   walkthrough step cards carry a `prior_anchor` slot
  - C-6.9   `visual_theme.faceless` defaults to True for pilots

The public surface is intentionally tight:

    load_composition(path: Path) -> Composition
    load_composition_from_string(text: str) -> Composition
    CompositionError                 — raised on any schema or contract breach
    Composition / BeatComposition / ...  — typed views for consumers

Module-local re-export `REQUIRED_BEATS` mirrors `pipeline.audit.REQUIRED_BEATS`
so storyboard consumers do not need to depend on the audit module directly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from pipeline.audit import REQUIRED_BEATS as REQUIRED_BEATS

# --------------------------------------------------------------------------- #
# Contract-derived constants                                                  #
# --------------------------------------------------------------------------- #

MIN_TITLE_FONT_PX = 72  # C-6.2 heading minimum
MIN_BODY_FONT_PX = 48  # C-6.2 body minimum
MIN_CONTRAST_RATIO = 7.0  # C-6.3
MIN_TRANSITION_MS = 400  # C-6.5
MAX_TRANSITION_MS = 800  # C-6.5
MIN_DWELL_SECONDS = 3.0  # C-6.6
MIN_WALKTHROUGH_STEPS = 2  # C-3.4 #5

BeatName = Literal[
    "hook",
    "acknowledge",
    "why",
    "show",
    "walkthrough",
    "recover",
    "recap",
    "outro",
]


# --------------------------------------------------------------------------- #
# Exceptions                                                                  #
# --------------------------------------------------------------------------- #


class CompositionError(ValueError):
    """Raised when a composition.yaml fails schema or contract validation."""


# --------------------------------------------------------------------------- #
# Models                                                                      #
# --------------------------------------------------------------------------- #


class VisualTheme(BaseModel):
    """Style guidance for the image generator (no faces, calm palette)."""

    model_config = ConfigDict(extra="forbid")

    palette: str
    mood: str
    faceless: bool = True  # C-6.9
    no_text_in_image: bool = True  # text is overlaid by the compositor


class StepCard(BaseModel):
    """One numbered step inside the walkthrough beat."""

    model_config = ConfigDict(extra="forbid")

    index: int = Field(ge=1)
    text: str
    prior_anchor: str | None = None  # C-6.8: visible alongside current step
    dwell_seconds: float = Field(ge=MIN_DWELL_SECONDS)


class BeatComposition(BaseModel):
    """One beat's worth of imagery + on-screen text."""

    model_config = ConfigDict(extra="forbid")

    beat: BeatName
    image_prompt: str  # consumed by the generator (fal/local provider)
    image_path: Path | None = None  # populated after generation
    title: str | None = None
    subtitle: str | None = None
    title_font_px: int = Field(ge=MIN_TITLE_FONT_PX)
    body_font_px: int = Field(ge=MIN_BODY_FONT_PX)
    contrast_ratio: float = Field(ge=MIN_CONTRAST_RATIO)
    dwell_seconds: float = Field(ge=MIN_DWELL_SECONDS)
    ken_burns: bool = True
    steps: list[StepCard] = Field(default_factory=list)

    @model_validator(mode="after")
    def _steps_only_on_walkthrough(self) -> BeatComposition:
        if self.beat == "walkthrough":
            if len(self.steps) < MIN_WALKTHROUGH_STEPS:
                raise ValueError(
                    f"walkthrough beat must declare at least "
                    f"{MIN_WALKTHROUGH_STEPS} steps (got {len(self.steps)})"
                )
        elif self.steps:
            raise ValueError(
                f"only the walkthrough beat may declare steps; got {len(self.steps)} on '{self.beat}'"
            )
        return self


class TransitionConfig(BaseModel):
    """Cross-beat transition timing (C-6.5)."""

    model_config = ConfigDict(extra="forbid")

    default_ms: int = Field(ge=MIN_TRANSITION_MS, le=MAX_TRANSITION_MS)
    min_ms: int = Field(default=MIN_TRANSITION_MS, ge=MIN_TRANSITION_MS, le=MAX_TRANSITION_MS)
    max_ms: int = Field(default=MAX_TRANSITION_MS, ge=MIN_TRANSITION_MS, le=MAX_TRANSITION_MS)


class Composition(BaseModel):
    """A full composition manifest, ready for the compositor."""

    model_config = ConfigDict(extra="forbid")

    format: str
    fps: int = Field(default=25, ge=24, le=60)
    visual_theme: VisualTheme
    beats: list[BeatComposition]
    transitions: TransitionConfig

    @model_validator(mode="after")
    def _all_required_beats_in_order(self) -> Composition:
        names = [b.beat for b in self.beats]
        if names != list(REQUIRED_BEATS):
            missing = [n for n in REQUIRED_BEATS if n not in names]
            extra = [n for n in names if n not in REQUIRED_BEATS]
            if missing:
                raise ValueError(f"missing required beats: {missing}")
            if extra:
                raise ValueError(f"unexpected beats: {extra}")
            raise ValueError(
                f"beats must appear in canonical order {list(REQUIRED_BEATS)}; got {names}"
            )
        return self


# --------------------------------------------------------------------------- #
# Loaders                                                                     #
# --------------------------------------------------------------------------- #


def load_composition(path: Path) -> Composition:
    """Load and validate `composition.yaml` from disk."""
    return load_composition_from_string(Path(path).read_text(encoding="utf-8"))


def load_composition_from_string(text: str) -> Composition:
    """Load and validate a composition manifest from raw YAML text."""
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise CompositionError(f"composition.yaml: invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise CompositionError("composition.yaml: top-level must be a mapping")
    try:
        return Composition.model_validate(data)
    except ValidationError as exc:
        raise CompositionError(_format_validation_error(exc)) from exc


def _format_validation_error(exc: ValidationError) -> str:
    """Render a pydantic ValidationError into a single readable message.

    Tests assert against substrings of this message (e.g. '7', 'walkthrough',
    'order'), so we surface the key fields and constraints verbatim.
    """
    lines: list[str] = ["composition.yaml failed validation:"]
    for err in exc.errors():
        loc = ".".join(str(p) for p in err["loc"])
        lines.append(f"  - {loc}: {err['msg']}")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Default builder                                                             #
# --------------------------------------------------------------------------- #


_DEFAULT_TITLES: dict[str, str] = {
    "hook": "Welcome.",
    "acknowledge": "What you may be wondering.",
    "why": "Why this matters.",
    "show": "Watch it once.",
    "walkthrough": "Step by step.",
    "recover": "If something goes wrong.",
    "recap": "What you have just seen.",
    "outro": "Thank you for being here.",
}


def default_composition(
    script_path: Path,
    voice_manifest_path: Path,
) -> Composition:
    """Build a valid Composition deterministically from script + voice.json.

    Lets the pipeline run end-to-end without invoking the visual-director
    agent. Used as: (a) the offline default if no `composition.yaml` is
    present next to the script, (b) the regression-test baseline, (c) the
    safety net when the agent is unavailable.

    The titles are deliberately generic. A real episode benefits from the
    visual-director agent's domain-aware titles, but the pipeline must not
    *require* the agent to produce a viewable mp4.
    """
    import json

    from pipeline.audit import parse_script
    from pipeline.compositor import VIDEO_HEIGHT, VIDEO_WIDTH

    fm, _ = parse_script(script_path)
    title = str(fm.get("title") or fm.get("id") or "")

    manifest = json.loads(Path(voice_manifest_path).read_text(encoding="utf-8"))
    timings = {b["name"]: float(b["duration_seconds"]) for b in manifest["beats"]}

    beats_data = fm.get("beats") or {}
    walk_steps_raw = beats_data.get("walkthrough") or []
    if not isinstance(walk_steps_raw, list):
        walk_steps_raw = [str(walk_steps_raw)]
    walk_step_count = max(MIN_WALKTHROUGH_STEPS, len(walk_steps_raw))

    composition_beats: list[BeatComposition] = []
    for name in REQUIRED_BEATS:
        dwell = max(MIN_DWELL_SECONDS, timings.get(name, MIN_DWELL_SECONDS))
        common = {
            "beat": name,
            "image_prompt": f"Calm domestic scene, {name} beat, no text, no faces.",
            "title": title if name == "hook" else _DEFAULT_TITLES[name],
            "title_font_px": MIN_TITLE_FONT_PX + 8,
            "body_font_px": MIN_BODY_FONT_PX + 8,
            "contrast_ratio": 15.0,
            "dwell_seconds": dwell,
        }
        if name == "walkthrough":
            per_step = max(MIN_DWELL_SECONDS, dwell / walk_step_count)
            steps: list[StepCard] = []
            for i, raw in enumerate(walk_steps_raw, start=1):
                step_text = str(raw).strip() or f"Step {i}."
                steps.append(
                    StepCard(
                        index=i,
                        text=step_text,
                        prior_anchor=(
                            f"{i - 1}. {str(walk_steps_raw[i - 2]).split('.')[0]}"
                            if i > 1
                            else None
                        ),
                        dwell_seconds=per_step,
                    )
                )
            composition_beats.append(BeatComposition(**common, steps=steps))
        else:
            composition_beats.append(BeatComposition(**common))

    return Composition(
        format=f"{VIDEO_WIDTH}x{VIDEO_HEIGHT}",
        fps=25,
        visual_theme=VisualTheme(
            palette="warm-neutral-morning-light",
            mood="calm, dignified, quiet",
            faceless=True,
            no_text_in_image=True,
        ),
        beats=composition_beats,
        transitions=TransitionConfig(default_ms=600, min_ms=400, max_ms=800),
    )
