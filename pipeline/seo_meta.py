"""SEO metadata schema (output of the SEO agent).

A `seo.yaml` file declares the YouTube-bound title, description, tags, and
chapter list. Used to populate `meta.yaml` for the publisher.

Contract clauses enforced at validation time:
- C-2.* / C-9.* no urgency, fear, or scarcity (forbidden phrase set is
  enforced by `pipeline.audit`; here we only enforce shape and length limits
  that the platform itself imposes).
"""

from __future__ import annotations

from itertools import pairwise
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator


class Chapter(BaseModel):
    start_seconds: float = Field(..., ge=0)
    title: str = Field(..., min_length=3, max_length=80)


class SeoMeta(BaseModel):
    title: str = Field(..., min_length=8, max_length=70)
    description: str = Field(..., min_length=40, max_length=4500)
    tags: list[str] = Field(default_factory=list, max_length=30)
    chapters: list[Chapter] = Field(default_factory=list)
    visibility: str = Field(default="public", pattern=r"^(public|unlisted|private)$")

    @field_validator("tags")
    @classmethod
    def _tags_shape(cls, v: list[str]) -> list[str]:
        for tag in v:
            if not (1 <= len(tag) <= 30):
                raise ValueError(f"tag length out of range [1,30]: {tag!r}")
            if "," in tag:
                raise ValueError(f"tag must not contain comma: {tag!r}")
        return v

    @field_validator("chapters")
    @classmethod
    def _chapters_monotonic(cls, v: list[Chapter]) -> list[Chapter]:
        if not v:
            return v
        if v[0].start_seconds != 0.0:
            raise ValueError("first chapter must start at 0.0 seconds (YouTube requirement)")
        for prev, cur in pairwise(v):
            if cur.start_seconds <= prev.start_seconds:
                raise ValueError("chapter starts must be strictly increasing")
        return v


def load_seo_meta(path: Path) -> SeoMeta:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return SeoMeta.model_validate(data)


def write_seo_meta(meta: SeoMeta, path: Path) -> None:
    Path(path).write_text(
        yaml.safe_dump(meta.model_dump(mode="json"), sort_keys=False),
        encoding="utf-8",
    )
