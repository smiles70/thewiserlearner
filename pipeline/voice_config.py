"""Voice configuration schema (output of the voice-director agent).

A `voice.yaml` file declares engine, voice id, rate, pitch, and the per-beat
pause map. Consumed by `pipeline.tts` when present; otherwise tts.py falls
back to its hard-coded defaults.

Contract clauses enforced at validation time:
- C-5.2 mean speech rate 110-120 wpm. We can't validate runtime wpm here, but
  we sanity-check the rate offset (Edge TTS percent string) is in a band that
  is unlikely to violate the contract.
- C-5.x pause grammar: pauses are in milliseconds, integer, in [0, 2500].
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator

# Edge TTS rate percent strings: "+0%", "-25%", "+10%". Allowed band -30%..+10%.
_RATE_RE = re.compile(r"^[+-]\d{1,2}%$")
_PITCH_RE = re.compile(r"^[+-]\d{1,3}Hz$")


class PauseEntry(BaseModel):
    after_beat: str = Field(..., min_length=2)
    duration_ms: int = Field(..., ge=0, le=2500)


class VoiceConfig(BaseModel):
    engine: str = Field(default="edge-tts", pattern=r"^[a-z0-9-]+$")
    voice: str = Field(..., min_length=4, max_length=80)
    rate: str = Field(default="-15%")
    pitch: str = Field(default="+0Hz")
    pauses: list[PauseEntry] = Field(default_factory=list)
    notes: str = ""

    @field_validator("rate")
    @classmethod
    def _rate_format(cls, v: str) -> str:
        if not _RATE_RE.match(v):
            raise ValueError(f"rate must look like '-15%' or '+0%': got {v!r}")
        offset = int(v.rstrip("%"))
        if offset < -30 or offset > 10:
            raise ValueError(f"rate offset {offset}% outside contract-safe band [-30, +10]")
        return v

    @field_validator("pitch")
    @classmethod
    def _pitch_format(cls, v: str) -> str:
        if not _PITCH_RE.match(v):
            raise ValueError(f"pitch must look like '+0Hz' or '-50Hz': got {v!r}")
        return v


def load_voice_config(path: Path) -> VoiceConfig:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return VoiceConfig.model_validate(data)


def write_voice_config(cfg: VoiceConfig, path: Path) -> None:
    Path(path).write_text(
        yaml.safe_dump(cfg.model_dump(mode="json"), sort_keys=False),
        encoding="utf-8",
    )


def default_voice_config() -> VoiceConfig:
    """Deterministic fallback when no voice-director run is available."""
    return VoiceConfig(
        engine="edge-tts",
        voice="en-US-AriaNeural",
        rate="-15%",
        pitch="+0Hz",
        pauses=[],
        notes="default fallback (voice-director agent not run)",
    )
