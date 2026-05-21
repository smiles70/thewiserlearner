"""Text-to-speech wrapper (Edge TTS).

Stubbed in v0.1.0: defines the interface that downstream parts will fill in.

The production implementation will:
  1. Read a contract-audited script.md
  2. Synthesise spoken-beat text via edge-tts with the C-5.1 voice
  3. Insert C-5.2 inter-step pauses (≥ 600 ms) between walkthrough steps
  4. Normalise loudness to -16 LUFS integrated (C-5.3) using ffmpeg `loudnorm`
  5. Write `voice.wav` next to the script and a `voice.json` timing manifest

The contract requirements this module enforces are tracked in
`contract/audit-rubric.md` checks A-5.4 through A-5.6.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class TTSResult:
    audio_path: Path
    timing_manifest_path: Path
    integrated_lufs: float
    true_peak_dbtp: float


def synthesise(script_path: Path, out_dir: Path) -> TTSResult:  # pragma: no cover - stub
    raise NotImplementedError(
        "pipeline.tts.synthesise is stubbed in v0.1.0. Implementation arrives "
        "in pipeline-part-6 (voice production)."
    )
