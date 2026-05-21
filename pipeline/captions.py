"""Caption generation and lint.

Stubbed in v0.1.0. The production implementation will:
  1. Transcribe `voice.wav` with faster-whisper (word-level timestamps)
  2. Emit SRT and VTT files honouring contract clauses:
     - C-7.2 caption pacing ≤ 160 wpm
     - C-7.2 ≤ 42 chars per line, ≤ 2 lines on screen
  3. Run a Flesch-Kincaid pass and emit a warning if grade > 9.0 (A-7.4)
  4. Write `captions.srt`, `captions.vtt`, `captions.json` next to the script
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class CaptionResult:
    srt_path: Path
    vtt_path: Path
    flesch_kincaid_grade: float


def generate(audio_path: Path, out_dir: Path) -> CaptionResult:  # pragma: no cover - stub
    raise NotImplementedError(
        "pipeline.captions.generate is stubbed in v0.1.0. Implementation "
        "arrives in pipeline-part-7 (captions and accessibility)."
    )
