"""Text-to-speech wrapper (Edge TTS).

Reads a contract-audited script, synthesises each beat with the C-5.1 voice,
inserts the C-5.2 inter-step pauses, normalises loudness to the C-5.3 target,
and writes `voice.wav` plus `voice.json` (timing manifest) next to the script.

Network calls are isolated in `_synth_one`. The planning logic in
`build_plan` is pure and unit-testable.

CLI:
    python -m pipeline.cli tts episodes/E-001-foo/script.md
"""

from __future__ import annotations

import asyncio
import json
import re
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from pipeline.audit import REQUIRED_BEATS, beat_text, parse_script

# Defaults track contract C-5.1..C-5.3. Voice is provisional per M-004.
DEFAULT_VOICE = "en-US-AriaNeural"
DEFAULT_RATE = "-25%"  # ~115 wpm out of Aria's default
DEFAULT_PITCH = "+0Hz"

INTER_STEP_PAUSE_MS = 700  # ≥ contract 600 ms minimum
INTER_BEAT_PAUSE_MS = 400

LUFS_TARGET = -16.0
TRUE_PEAK_MAX = -1.5
SAMPLE_RATE = 48_000


# --------------------------------------------------------------------------- #
# Plan (pure, testable)                                                       #
# --------------------------------------------------------------------------- #


@dataclass
class Segment:
    """A unit of audio to render: either spoken text or a silent pause."""

    kind: str  # "speech" | "silence"
    name: str
    text: str = ""
    duration_ms: int = 0


@dataclass
class Plan:
    """Ordered list of segments derived from a script's beats."""

    segments: list[Segment] = field(default_factory=list)
    beat_segment_ranges: dict[str, tuple[int, int]] = field(default_factory=dict)


def build_plan(beats: dict[str, Any]) -> Plan:
    """Build a render plan from a beats mapping.

    Walkthrough steps each become their own speech segment with an inter-step
    silence between them. All other beats become a single speech segment.
    A short inter-beat silence sits between every beat.
    """
    plan = Plan()
    for beat_name in REQUIRED_BEATS:
        start = len(plan.segments)
        if beat_name == "walkthrough":
            steps = beats.get("walkthrough") or []
            if not isinstance(steps, list):
                steps = [str(steps)]
            for i, step in enumerate(steps):
                step_text = str(step).strip()
                if not step_text:
                    continue
                plan.segments.append(Segment("speech", f"walk_{i}", text=step_text))
                if i < len(steps) - 1:
                    plan.segments.append(
                        Segment("silence", f"walk_pause_{i}", duration_ms=INTER_STEP_PAUSE_MS)
                    )
        else:
            text = beat_text(beats.get(beat_name, ""))
            if not text:
                continue
            plan.segments.append(Segment("speech", beat_name, text=text))

        end = len(plan.segments)
        if end > start:
            plan.beat_segment_ranges[beat_name] = (start, end)
            # inter-beat pause (omit after the final beat)
            if beat_name != REQUIRED_BEATS[-1]:
                plan.segments.append(
                    Segment("silence", f"{beat_name}_pause", duration_ms=INTER_BEAT_PAUSE_MS)
                )
    return plan


# --------------------------------------------------------------------------- #
# Result                                                                      #
# --------------------------------------------------------------------------- #


@dataclass
class BeatTiming:
    name: str
    start_seconds: float
    duration_seconds: float


@dataclass
class TTSResult:
    audio_path: Path
    timing_manifest_path: Path
    integrated_lufs: float | None
    true_peak_dbtp: float | None
    duration_seconds: float
    beats: list[BeatTiming]


# --------------------------------------------------------------------------- #
# Public entry point                                                          #
# --------------------------------------------------------------------------- #


def synthesise(
    script_path: Path,
    out_dir: Path,
    *,
    voice: str = DEFAULT_VOICE,
    rate: str = DEFAULT_RATE,
    pitch: str = DEFAULT_PITCH,
) -> TTSResult:
    """Synthesise a contract-audited script to ``out_dir/voice.wav``.

    Requires ``ffmpeg`` and ``ffprobe`` on PATH. Hits the Microsoft Edge TTS
    backend over the network — do not call from CI without an
    ``EDGE_TTS_LIVE=1`` opt-in.
    """
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise RuntimeError("ffmpeg and ffprobe must be on PATH")

    fm, _ = parse_script(script_path)
    beats = fm.get("beats") or {}
    plan = build_plan(beats)
    if not plan.segments:
        raise ValueError(f"{script_path}: no spoken segments after planning")

    out_dir.mkdir(parents=True, exist_ok=True)
    workdir = Path(tempfile.mkdtemp(prefix="wl-tts-"))
    try:
        rendered = asyncio.run(_render_segments(plan, workdir, voice, rate, pitch))
        concat = _concat(rendered, workdir)
        final_wav = out_dir / "voice.wav"
        lufs, tp = _loudnorm(concat, final_wav)
        durations_s = [_audio_duration(p) for p in rendered]
        timings = _compute_beat_timings(plan, durations_s)
        total = _audio_duration(final_wav)
        manifest = {
            "script_path": str(script_path),
            "voice": voice,
            "rate": rate,
            "pitch": pitch,
            "duration_seconds": total,
            "integrated_lufs": lufs,
            "true_peak_dbtp": tp,
            "beats": [asdict(b) for b in timings],
        }
        manifest_path = out_dir / "voice.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return TTSResult(
            audio_path=final_wav,
            timing_manifest_path=manifest_path,
            integrated_lufs=lufs,
            true_peak_dbtp=tp,
            duration_seconds=total,
            beats=timings,
        )
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _compute_beat_timings(plan: Plan, durations_s: list[float]) -> list[BeatTiming]:
    """Map per-segment durations back to per-beat (start, duration) pairs."""
    cursor = 0.0
    cumulative: list[float] = []
    for d in durations_s:
        cumulative.append(cursor)
        cursor += d
    timings: list[BeatTiming] = []
    for beat, (start_idx, end_idx) in plan.beat_segment_ranges.items():
        start_t = cumulative[start_idx]
        end_t = cumulative[end_idx - 1] + durations_s[end_idx - 1]
        timings.append(BeatTiming(beat, start_t, end_t - start_t))
    return timings


# --------------------------------------------------------------------------- #
# Rendering primitives (network + ffmpeg)                                     #
# --------------------------------------------------------------------------- #


async def _render_segments(
    plan: Plan, workdir: Path, voice: str, rate: str, pitch: str
) -> list[Path]:
    paths: list[Path] = []
    for seg in plan.segments:
        if seg.kind == "speech":
            paths.append(await _synth_one(seg.text, voice, rate, pitch, workdir, seg.name))
        else:
            paths.append(_silence(workdir, seg.name, seg.duration_ms))
    return paths


async def _synth_one(  # pragma: no cover - network
    text: str, voice: str, rate: str, pitch: str, workdir: Path, name: str
) -> Path:
    import edge_tts

    mp3 = workdir / f"{name}.mp3"
    wav = workdir / f"{name}.wav"
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await communicate.save(str(mp3))
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(mp3),
            "-ar",
            str(SAMPLE_RATE),
            "-ac",
            "1",
            str(wav),
        ],
        check=True,
    )
    return wav


def _silence(workdir: Path, name: str, ms: int) -> Path:
    wav = workdir / f"{name}.wav"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"anullsrc=r={SAMPLE_RATE}:cl=mono",
            "-t",
            f"{ms / 1000.0:.3f}",
            str(wav),
        ],
        check=True,
    )
    return wav


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


def _concat(segments: list[Path], workdir: Path) -> Path:
    list_file = workdir / "concat.txt"
    list_file.write_text("\n".join(f"file '{s.as_posix()}'" for s in segments), encoding="utf-8")
    out = workdir / "concat.wav"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-ar",
            str(SAMPLE_RATE),
            "-ac",
            "1",
            str(out),
        ],
        check=True,
    )
    return out


_LOUDNORM_JSON_RE = re.compile(r"\{[^{}]*\"input_i\"[\s\S]*?\}")


def _loudnorm(input_wav: Path, output_wav: Path) -> tuple[float | None, float | None]:
    """Single-pass loudnorm. Adequate for v0.1; two-pass can be added later."""
    res = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "info",
            "-i",
            str(input_wav),
            "-af",
            f"loudnorm=I={LUFS_TARGET}:TP={TRUE_PEAK_MAX}:LRA=11:print_format=json",
            "-ar",
            str(SAMPLE_RATE),
            "-ac",
            "1",
            str(output_wav),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    m = _LOUDNORM_JSON_RE.search(res.stderr)
    if not m:
        return None, None
    try:
        info = json.loads(m.group(0))
        return float(info.get("output_i")), float(info.get("output_tp"))
    except (ValueError, TypeError):
        return None, None
