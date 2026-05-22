"""Episode brief schema.

A brief is the upstream artefact that drives the scripter. It declares the
topic, target capability, runtime, level, and the library entries that the
script must cite. Loaded by the scripter agent; validated by pydantic before
any LLM call to fail fast on bad inputs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator


class Brief(BaseModel):
    """Inputs to the scripter agent for one episode."""

    id: str = Field(..., pattern=r"^E-\d{3}-[a-z0-9-]+$")
    title: str = Field(..., min_length=4, max_length=80)
    topic: str = Field(..., min_length=8, max_length=400)
    target_capability: str = Field(..., min_length=4, max_length=200)
    target_runtime_seconds: int = Field(..., ge=180, le=600)
    level: Literal["intro", "intermediate", "advanced"] = "intro"
    library_refs: list[str] = Field(default_factory=list)
    notes: str = ""

    @field_validator("library_refs")
    @classmethod
    def _refs_are_l_codes(cls, v: list[str]) -> list[str]:
        for ref in v:
            if not ref.startswith("L-") or len(ref) < 5:
                raise ValueError(f"library ref must look like 'L-001-...': got {ref!r}")
        return v


def load_brief(path: Path) -> Brief:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return Brief.model_validate(data)


def write_brief(brief: Brief, path: Path) -> None:
    Path(path).write_text(
        yaml.safe_dump(brief.model_dump(mode="json"), sort_keys=False),
        encoding="utf-8",
    )
