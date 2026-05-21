"""Caption generation and lint.

Generates SRT and VTT captions from a contract-audited ``script.md`` and the
``voice.json`` timing manifest produced by ``pipeline.tts``.

v0.1 strategy: use script text (canonical) for cue content, and the per-beat
timings from ``voice.json`` to time the cues. Within a beat, cue durations are
distributed proportional to word count. This is good enough for older-adult
caption pacing (the contract's reading-rate budget is the binding constraint,
not millisecond word-level precision) and avoids requiring faster-whisper at
v0.1.

A future v0.2 can swap in whisper word-level timing without changing the
public interface of ``generate``.

Contract clauses honoured:
  - C-7.1 captions are mandatory, in SRT and VTT
  - C-7.2 ≤ 42 chars per line, ≤ 2 lines per cue
  - C-7.2 each cue duration >= max(1.5 s, words * 0.375 s)  (<= 160 wpm)
  - C-7.4 Flesch-Kincaid grade ≤ 9.0 (warning, not block)
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from pipeline.audit import REQUIRED_BEATS, beat_text, parse_script

MAX_LINE_CHARS = 42
MAX_LINES_PER_CUE = 2
MIN_CUE_SECONDS = 1.5
SECONDS_PER_WORD = 0.375  # ≤ 160 wpm reading rate

FK_GRADE_LIMIT = 9.0


# --------------------------------------------------------------------------- #
# Data classes                                                                #
# --------------------------------------------------------------------------- #


@dataclass
class Cue:
    index: int
    start_seconds: float
    end_seconds: float
    lines: list[str]

    @property
    def text(self) -> str:
        return " ".join(self.lines)

    @property
    def words(self) -> int:
        return len(re.findall(r"\b\w[\w'-]*\b", self.text))


@dataclass
class CaptionResult:
    srt_path: Path
    vtt_path: Path
    json_path: Path
    cues: list[Cue] = field(default_factory=list)
    flesch_kincaid_grade: float = 0.0
    over_grade_limit: bool = False


# --------------------------------------------------------------------------- #
# Pure helpers                                                                #
# --------------------------------------------------------------------------- #


_WORD_RE = re.compile(r"\S+")


def wrap_to_lines(text: str, max_chars: int = MAX_LINE_CHARS) -> list[str]:
    """Greedy word-wrap into lines no longer than ``max_chars``."""
    words = _WORD_RE.findall(text.strip())
    lines: list[str] = []
    current = ""
    for w in words:
        if not current:
            current = w
        elif len(current) + 1 + len(w) <= max_chars:
            current = f"{current} {w}"
        else:
            lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines


def chunk_lines_into_cues(lines: list[str], max_lines: int = MAX_LINES_PER_CUE) -> list[list[str]]:
    """Group wrapped lines into cue-sized blocks (≤ ``max_lines`` per cue)."""
    return [lines[i : i + max_lines] for i in range(0, len(lines), max_lines)]


def min_cue_seconds(words: int) -> float:
    """Contract C-7.2 minimum duration for a cue containing ``words`` words."""
    return max(MIN_CUE_SECONDS, words * SECONDS_PER_WORD)


def distribute_durations(
    word_counts: list[int], total_seconds: float, *, min_per_cue: float = MIN_CUE_SECONDS
) -> list[float]:
    """Distribute ``total_seconds`` across cues proportional to word counts.

    Each cue is guaranteed at least ``min_per_cue`` seconds. If the total
    minimum exceeds ``total_seconds``, we honour the minimum and let the cues
    overrun the beat — caption legibility wins over strict beat sync.
    """
    n = len(word_counts)
    if n == 0:
        return []
    minimums = [max(min_per_cue, w * SECONDS_PER_WORD) for w in word_counts]
    min_total = sum(minimums)
    if min_total >= total_seconds:
        return minimums
    extra = total_seconds - min_total
    total_words = sum(word_counts) or 1
    return [m + extra * (w / total_words) for m, w in zip(minimums, word_counts, strict=False)]


def _format_timestamp(seconds: float, *, comma: bool) -> str:
    """Format seconds as ``HH:MM:SS,mmm`` (SRT) or ``HH:MM:SS.mmm`` (VTT)."""
    if seconds < 0:
        seconds = 0.0
    millis = round(seconds * 1000)
    h, rem = divmod(millis, 3600 * 1000)
    m, rem = divmod(rem, 60 * 1000)
    s, ms = divmod(rem, 1000)
    sep = "," if comma else "."
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def format_srt(cues: list[Cue]) -> str:
    chunks: list[str] = []
    for c in cues:
        start = _format_timestamp(c.start_seconds, comma=True)
        end = _format_timestamp(c.end_seconds, comma=True)
        body = "\n".join(c.lines)
        chunks.append(f"{c.index}\n{start} --> {end}\n{body}\n")
    return "\n".join(chunks)


def format_vtt(cues: list[Cue]) -> str:
    parts = ["WEBVTT", ""]
    for c in cues:
        start = _format_timestamp(c.start_seconds, comma=False)
        end = _format_timestamp(c.end_seconds, comma=False)
        body = "\n".join(c.lines)
        parts.append(f"{c.index}\n{start} --> {end}\n{body}\n")
    return "\n".join(parts)


# --------------------------------------------------------------------------- #
# Flesch-Kincaid                                                              #
# --------------------------------------------------------------------------- #


_VOWEL_RE = re.compile(r"[aeiouy]+", re.IGNORECASE)
_SENT_END_RE = re.compile(r"[.!?]+")


def _count_syllables(word: str) -> int:
    word = word.lower().strip("'\"-.,;:!?()")
    if not word:
        return 0
    if len(word) <= 3:
        return 1
    syl = len(_VOWEL_RE.findall(word))
    if word.endswith("e") and syl > 1 and not word.endswith("le"):
        syl -= 1
    return max(1, syl)


def flesch_kincaid_grade(text: str) -> float:
    """Compute the Flesch-Kincaid grade level of ``text``.

    Returns 0.0 for trivially short input.
    """
    sentences = [s for s in _SENT_END_RE.split(text) if s.strip()]
    words = re.findall(r"\b[\w'-]+\b", text)
    if not sentences or not words:
        return 0.0
    syllables = sum(_count_syllables(w) for w in words)
    grade = 0.39 * (len(words) / len(sentences)) + 11.8 * (syllables / len(words)) - 15.59
    return round(grade, 2)


# --------------------------------------------------------------------------- #
# Public entry point                                                          #
# --------------------------------------------------------------------------- #


def generate(
    script_path: Path,
    voice_manifest_path: Path,
    out_dir: Path,
) -> CaptionResult:
    """Generate ``captions.srt`` and ``captions.vtt`` from script + voice timing.

    The script supplies the canonical text. The voice manifest supplies the
    per-beat (start, duration) pairs produced by ``pipeline.tts.synthesise``.
    """
    fm, _ = parse_script(script_path)
    beats = fm.get("beats") or {}

    manifest = json.loads(voice_manifest_path.read_text(encoding="utf-8"))
    beat_timings = {
        b["name"]: (b["start_seconds"], b["duration_seconds"]) for b in manifest["beats"]
    }

    cues = build_cues_from_beats(beats, beat_timings)

    out_dir.mkdir(parents=True, exist_ok=True)
    srt_path = out_dir / "captions.srt"
    vtt_path = out_dir / "captions.vtt"
    json_path = out_dir / "captions.json"
    srt_path.write_text(format_srt(cues), encoding="utf-8")
    vtt_path.write_text(format_vtt(cues), encoding="utf-8")

    full_text = " ".join(c.text for c in cues)
    grade = flesch_kincaid_grade(full_text)
    json_path.write_text(
        json.dumps(
            {
                "script_path": str(script_path),
                "voice_manifest": str(voice_manifest_path),
                "flesch_kincaid_grade": grade,
                "over_grade_limit": grade > FK_GRADE_LIMIT,
                "cues": [asdict(c) for c in cues],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    return CaptionResult(
        srt_path=srt_path,
        vtt_path=vtt_path,
        json_path=json_path,
        cues=cues,
        flesch_kincaid_grade=grade,
        over_grade_limit=grade > FK_GRADE_LIMIT,
    )


def build_cues_from_beats(beats: dict, beat_timings: dict[str, tuple[float, float]]) -> list[Cue]:
    """Pure: derive the full ordered list of Cue objects."""
    cues: list[Cue] = []
    next_index = 1
    for beat_name in REQUIRED_BEATS:
        timing = beat_timings.get(beat_name)
        if timing is None:
            continue
        start, duration = timing
        if beat_name == "walkthrough":
            steps = beats.get("walkthrough") or []
            if not isinstance(steps, list):
                steps = [str(steps)]
            text_blocks = [str(s).strip() for s in steps if str(s).strip()]
        else:
            text = beat_text(beats.get(beat_name, ""))
            if not text:
                continue
            text_blocks = [text]
        block_word_counts = [len(re.findall(r"\b\w[\w'-]*\b", b)) for b in text_blocks]
        block_durations = distribute_durations(block_word_counts, duration)
        cursor = start
        for block, block_dur in zip(text_blocks, block_durations, strict=False):
            lines = wrap_to_lines(block)
            cue_blocks = chunk_lines_into_cues(lines)
            cue_word_counts = [len(re.findall(r"\b\w[\w'-]*\b", " ".join(b))) for b in cue_blocks]
            cue_durations = distribute_durations(cue_word_counts, block_dur)
            for cue_lines, cue_dur in zip(cue_blocks, cue_durations, strict=False):
                cues.append(
                    Cue(
                        index=next_index,
                        start_seconds=cursor,
                        end_seconds=cursor + cue_dur,
                        lines=cue_lines,
                    )
                )
                next_index += 1
                cursor += cue_dur
    return cues
