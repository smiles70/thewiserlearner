"""Video composition (FFmpeg).

The compositor has two paths, both contract-compliant:

  v0.1 (single-card)   composite(voice_path, captions_srt, script_path, out_dir)
  v0.2 (per-beat)      composite_with_composition(voice_path, captions_srt,
                           composition, visuals, voice_manifest_path, out_dir)

The v0.1 path renders one Pillow title card for the full episode duration —
useful when no `composition.yaml` is present, and as the unconditional safety
net. The v0.2 path renders per-beat backgrounds (provided by a VisualProvider)
joined with Ken Burns zoompan and 400-800 ms xfade transitions, with step
overlays during the walkthrough beat to satisfy C-6.8.

The filter-graph idiom for v0.2 was empirically validated by
`scripts/spike_filter_graph.py`. See that script for the canonical pattern;
this module reuses the same `zoompan d=1` + cumulative-offset xfade chain
adapted for variable per-segment durations.

Contract clauses honoured by both paths:
  - C-6.1 1920x1080 16:9
  - C-6.2 typography (heading >= 72 px; body >= 48 px)
  - C-6.3 contrast >= 7:1 (white on near-black)
  - C-6.5 transitions are between 400 and 800 ms; no rapid motion within a beat
  - C-6.8 walkthrough step number + prior step anchor remain visible
  - C-7.1 captions burned in
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
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

# v0.2 Ken Burns: subtle zoom from 1.0 -> ZOOM_END across each segment.
# Conservative value chosen to honour C-6.5 ("no rapid motion") while still
# providing enough motion to keep older eyes engaged on a static background.
KEN_BURNS_ZOOM_END = 1.04


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


# =========================================================================== #
# v0.2 — per-beat composition with Ken Burns + xfade + step overlays          #
# =========================================================================== #


@dataclass
class Segment:
    """One image-backed slice of the timeline.

    For non-walkthrough beats, exactly one Segment is created per beat.
    For the walkthrough beat, one Segment is created per step. The
    `image_path` is either the raw beat background (non-walkthrough) or a
    Pillow-stamped variant of it (walkthrough, with step number + prior
    anchor overlaid; see ``render_walkthrough_step_overlay``).
    """

    image_path: Path
    duration_seconds: float
    title: str | None = None  # baked-in via Pillow before ffmpeg sees it
    subtitle: str | None = None
    # diagnostic-only, never affects ffmpeg output:
    beat: str = ""
    step_index: int | None = None


@dataclass
class CompositionResult:
    """Result of `composite_with_composition`. Superset of v0.1 CompositeResult."""

    video_path: Path
    duration_seconds: float
    segment_count: int
    segments: list[Segment] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Step-overlay rendering (Pillow, deterministic, offline)                     #
# --------------------------------------------------------------------------- #


def _draw_text_block(
    img,
    draw,
    *,
    lines: list[str],
    top_y: int,
    font_px: int,
    color: tuple[int, int, int],
    max_width_px: int,
) -> int:
    """Draw a list of pre-wrapped lines centred horizontally. Returns the
    final y after the block."""
    font = _resolve_font(font_px)
    y = top_y
    for line in lines:
        line_w = draw.textlength(line, font=font)
        x = (img.width - line_w) / 2
        # Soft text shadow for legibility against any background.
        draw.text(
            (x + 2, y + 2),
            line,
            fill=(0, 0, 0),
            font=font,
        )
        draw.text((x, y), line, fill=color, font=font)
        y += int(font_px * 1.3)
    return y


def render_beat_card(
    base_image: Path,
    out_path: Path,
    *,
    title: str | None,
    subtitle: str | None = None,
    title_font_px: int = TITLE_FONT_PX,
    subtitle_font_px: int = SUBTITLE_FONT_PX,
) -> Path:
    """Stamp a title (and optional subtitle) onto a beat's background image."""
    from PIL import Image, ImageDraw

    img = Image.open(base_image).convert("RGB")
    draw = ImageDraw.Draw(img)
    margin = int(img.width * 0.08)
    text_max = img.width - 2 * margin

    if title:
        title_font = _resolve_font(title_font_px)
        title_lines = _wrap_words(title, title_font, draw, text_max)
        _draw_text_block(
            img,
            draw,
            lines=title_lines,
            top_y=int(img.height * 0.30),
            font_px=title_font_px,
            color=FOREGROUND_RGB,
            max_width_px=text_max,
        )
    if subtitle:
        sub_font = _resolve_font(subtitle_font_px)
        sub_lines = _wrap_words(subtitle, sub_font, draw, text_max)
        _draw_text_block(
            img,
            draw,
            lines=sub_lines,
            top_y=int(img.height * 0.58),
            font_px=subtitle_font_px,
            color=ACCENT_RGB,
            max_width_px=text_max,
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG", optimize=True)
    return out_path


def render_walkthrough_step_overlay(
    base_image: Path,
    out_path: Path,
    *,
    step_index: int,
    step_text: str,
    prior_anchor: str | None,
    title: str | None,
    title_font_px: int = TITLE_FONT_PX,
    body_font_px: int = SUBTITLE_FONT_PX,
) -> Path:
    """Stamp the current step number + prior anchor (C-6.8) onto a card.

    Layout (top to bottom):
      - title (if any), top-third of frame
      - "Step N" badge mid-frame
      - "Previously: <prior_anchor>" near the bottom (skipped on step 1)

    Note: the spoken step text itself is NOT drawn here — it is delivered by
    the burned-in captions (SRT) that the compositor overlays via ffmpeg's
    `subtitles=` filter. Drawing it on the card too would produce a visible
    double-render. The `step_text` argument is retained for callsite
    compatibility and may be logged or audited but is intentionally unused
    in the image layout.
    """
    from PIL import Image, ImageDraw

    img = Image.open(base_image).convert("RGB")
    draw = ImageDraw.Draw(img)
    margin = int(img.width * 0.08)
    text_max = img.width - 2 * margin

    if title:
        title_font = _resolve_font(title_font_px)
        title_lines = _wrap_words(title, title_font, draw, text_max)
        _draw_text_block(
            img,
            draw,
            lines=title_lines,
            top_y=int(img.height * 0.18),
            font_px=title_font_px,
            color=FOREGROUND_RGB,
            max_width_px=text_max,
        )

    # Step badge.
    badge_font_px = max(56, body_font_px)
    badge_text = f"Step {step_index}"
    _draw_text_block(
        img,
        draw,
        lines=[badge_text],
        top_y=int(img.height * 0.46),
        font_px=badge_font_px,
        color=ACCENT_RGB,
        max_width_px=text_max,
    )

    # Step text is intentionally NOT drawn on the card; the burned SRT
    # captions are the single source of on-screen dialogue (see docstring).
    _ = step_text  # explicit no-op so linters don't flag the unused arg

    # Prior anchor footer (C-6.8).
    if prior_anchor:
        anchor_font_px = max(40, body_font_px - 8)
        anchor_font = _resolve_font(anchor_font_px)
        anchor_lines = _wrap_words(f"Previously: {prior_anchor}", anchor_font, draw, text_max)
        _draw_text_block(
            img,
            draw,
            lines=anchor_lines,
            top_y=int(img.height * 0.84),
            font_px=anchor_font_px,
            color=ACCENT_RGB,
            max_width_px=text_max,
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG", optimize=True)
    return out_path


# --------------------------------------------------------------------------- #
# Segment expansion                                                           #
# --------------------------------------------------------------------------- #


def expand_segments(
    composition,  # pipeline.storyboard.Composition (avoid hard import cycle)
    visuals,  # dict[str, pipeline.visuals.VisualResult]
    voice_timings: dict[str, float],
    out_dir: Path,
) -> list[Segment]:
    """Expand a Composition into a flat list of timeline Segments.

    Walkthrough beats expand into N step-overlaid sub-segments. Their
    durations are taken from the composition's per-step ``dwell_seconds``.
    Other beats produce a single titled Segment with a duration matching
    the voice timing for that beat, falling back to the composition's
    declared ``dwell_seconds`` if the voice manifest lacks the beat.
    """
    segments_dir = out_dir / "segments"
    segments_dir.mkdir(parents=True, exist_ok=True)

    segments: list[Segment] = []
    for beat in composition.beats:
        base_path = visuals[beat.beat].image_path
        beat_duration = float(voice_timings.get(beat.beat, beat.dwell_seconds))

        if beat.beat == "walkthrough" and beat.steps:
            # Distribute the beat's voice duration across the declared steps
            # in proportion to their declared dwell_seconds. Captions still
            # carry the verbatim narration; these segments only need to
            # advance roughly in sync.
            declared = [s.dwell_seconds for s in beat.steps]
            total_declared = sum(declared) or 1.0
            for step in beat.steps:
                seg_path = segments_dir / f"walkthrough_step_{step.index}.png"
                render_walkthrough_step_overlay(
                    base_path,
                    seg_path,
                    step_index=step.index,
                    step_text=step.text,
                    prior_anchor=step.prior_anchor,
                    title=beat.title,
                )
                seg_dur = beat_duration * (step.dwell_seconds / total_declared)
                segments.append(
                    Segment(
                        image_path=seg_path,
                        duration_seconds=seg_dur,
                        title=beat.title,
                        beat=beat.beat,
                        step_index=step.index,
                    )
                )
        else:
            seg_path = segments_dir / f"{beat.beat}.png"
            render_beat_card(
                base_path,
                seg_path,
                title=beat.title,
                subtitle=beat.subtitle,
                title_font_px=beat.title_font_px,
                subtitle_font_px=beat.body_font_px,
            )
            segments.append(
                Segment(
                    image_path=seg_path,
                    duration_seconds=beat_duration,
                    title=beat.title,
                    subtitle=beat.subtitle,
                    beat=beat.beat,
                )
            )
    return segments


# --------------------------------------------------------------------------- #
# Multi-segment ffmpeg command builder (pure)                                 #
# --------------------------------------------------------------------------- #


def build_ffmpeg_command_multi(
    segments: list[Segment],
    voice_path: Path,
    captions_srt: Path | None,
    xfade_ms: int,
    out_path: Path,
    *,
    fps: int = VIDEO_FPS,
    width: int = VIDEO_WIDTH,
    height: int = VIDEO_HEIGHT,
) -> list[str]:
    """Build the ffmpeg command for a per-beat render. Pure: easy to test.

    Strategy (validated by ``scripts/spike_filter_graph.py``):
      * each image is a ``-loop 1 -t Ti`` input
      * each input goes through scale -> pad -> setsar=1 -> zoompan(d=1) ->
        format -> fps -> setpts to a labelled ``[vN]`` stream
      * the streams are joined with cumulative-offset xfade transitions
      * the final video stream gets the subtitles burn-in filter

    Variable-duration arithmetic for the xfade chain:
      offset_k = (sum of T0..Tk-1) - k * X      where X = xfade_ms / 1000
    The accumulating offset accounts for the fact that each xfade overlaps
    its predecessor by X seconds.
    """
    if not segments:
        raise ValueError("build_ffmpeg_command_multi requires at least one segment")
    if xfade_ms < 400 or xfade_ms > 800:
        raise ValueError(f"xfade_ms must be in [400, 800] (C-6.5); got {xfade_ms}")

    xfade_s = xfade_ms / 1000.0

    cmd: list[str] = ["ffmpeg", "-y", "-loglevel", "error"]
    for seg in segments:
        cmd.extend(
            [
                "-loop",
                "1",
                "-t",
                f"{seg.duration_seconds:.3f}",
                "-framerate",
                str(fps),
                "-i",
                str(seg.image_path),
            ]
        )
    cmd.extend(["-i", str(voice_path)])

    # Per-segment normalisation + Ken Burns.
    parts: list[str] = []
    for i, seg in enumerate(segments):
        total_frames = max(1, int(seg.duration_seconds * fps))
        inc = (KEN_BURNS_ZOOM_END - 1.0) / total_frames
        zoom_expr = f"min(zoom+{inc:.6f},{KEN_BURNS_ZOOM_END:.4f})"
        parts.append(
            f"[{i}:v]"
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"setsar=1,"
            f"zoompan=z='{zoom_expr}':d=1:s={width}x{height}:fps={fps}"
            f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)',"
            f"format=yuv420p,fps={fps},"
            f"setpts=PTS-STARTPTS"
            f"[v{i}]"
        )

    # xfade chain. With segments of varying length T_i and an xfade of length
    # X seconds, segment k must begin to crossfade at:
    #   offset_k = (T_0 + T_1 + ... + T_{k-1}) - k * X
    # i.e. cumulative-prefix-duration minus the time eaten by previous fades.
    if len(segments) == 1:
        prev_label = "v0"
    else:
        cumulative = 0.0
        prev_label = "v0"
        for k in range(1, len(segments)):
            cumulative += segments[k - 1].duration_seconds
            offset = cumulative - k * xfade_s
            label = f"x{k}"
            parts.append(
                f"[{prev_label}][v{k}]"
                f"xfade=transition=fade:duration={xfade_s:.3f}:offset={offset:.3f}"
                f"[{label}]"
            )
            prev_label = label

    if captions_srt is not None:
        srt_arg = str(captions_srt).replace("\\", "/").replace(":", r"\:")
        parts.append(
            f"[{prev_label}]subtitles='{srt_arg}':force_style="
            "'Fontname=Arial,Fontsize=22,PrimaryColour=&H00FFFFFF,"
            "BackColour=&HB2000000,BorderStyle=4,Outline=0,Shadow=0,"
            "Alignment=2,MarginV=70'[vout]"
        )
        video_map = "[vout]"
    else:
        video_map = f"[{prev_label}]"

    audio_input_index = len(segments)
    cmd.extend(
        [
            "-filter_complex",
            ";".join(parts),
            "-map",
            video_map,
            "-map",
            f"{audio_input_index}:a",
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


# --------------------------------------------------------------------------- #
# v0.2 entry point                                                            #
# --------------------------------------------------------------------------- #


def composite_with_composition(
    voice_path: Path,
    captions_srt: Path | None,
    composition,  # pipeline.storyboard.Composition
    visuals,  # dict[str, pipeline.visuals.VisualResult]
    voice_manifest_path: Path,
    out_dir: Path,
) -> CompositionResult:
    """Render an MP4 using the per-beat composition manifest.

    Requires ``ffmpeg`` and ``ffprobe`` on PATH and an external `visuals`
    mapping (typically produced by `pipeline.visuals.generate_all`).
    """
    import json

    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise RuntimeError("ffmpeg and ffprobe must be on PATH")
    if not voice_path.is_file():
        raise FileNotFoundError(voice_path)

    manifest = json.loads(Path(voice_manifest_path).read_text(encoding="utf-8"))
    voice_timings = {b["name"]: float(b["duration_seconds"]) for b in manifest["beats"]}

    out_dir.mkdir(parents=True, exist_ok=True)
    segments = expand_segments(composition, visuals, voice_timings, out_dir)

    final_mp4 = out_dir / "episode.mp4"
    cmd = build_ffmpeg_command_multi(
        segments,
        voice_path,
        captions_srt,
        xfade_ms=composition.transitions.default_ms,
        out_path=final_mp4,
        fps=composition.fps,
    )
    subprocess.run(cmd, check=True)

    duration = _audio_duration(final_mp4)
    return CompositionResult(
        video_path=final_mp4,
        duration_seconds=duration,
        segment_count=len(segments),
        segments=segments,
    )
