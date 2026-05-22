"""Tests for brief, voice_config, and seo_meta schemas."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from pipeline.brief import Brief, load_brief, write_brief
from pipeline.seo_meta import Chapter, SeoMeta, load_seo_meta, write_seo_meta
from pipeline.voice_config import (
    VoiceConfig,
    default_voice_config,
    load_voice_config,
    write_voice_config,
)

# ---------- Brief ----------


def _good_brief() -> dict:
    return {
        "id": "E-001-ai-is-everywhere",
        "title": "AI is everywhere",
        "topic": "Help older adults notice the AI already in their daily tools.",
        "target_capability": "Recognise three places AI runs invisibly.",
        "target_runtime_seconds": 300,
        "level": "intro",
        "library_refs": ["L-001-knowles-2020", "L-007-czaja-2019"],
    }


def test_brief_accepts_valid():
    b = Brief.model_validate(_good_brief())
    assert b.id == "E-001-ai-is-everywhere"
    assert b.target_runtime_seconds == 300


def test_brief_rejects_bad_id():
    bad = _good_brief() | {"id": "001 ai everywhere"}
    with pytest.raises(ValidationError):
        Brief.model_validate(bad)


def test_brief_rejects_runtime_below_180():
    bad = _good_brief() | {"target_runtime_seconds": 60}
    with pytest.raises(ValidationError):
        Brief.model_validate(bad)


def test_brief_rejects_non_l_ref():
    bad = _good_brief() | {"library_refs": ["X-999-bogus"]}
    with pytest.raises(ValidationError):
        Brief.model_validate(bad)


def test_brief_round_trip(tmp_path: Path):
    b = Brief.model_validate(_good_brief())
    p = tmp_path / "brief.yaml"
    write_brief(b, p)
    b2 = load_brief(p)
    assert b2 == b


# ---------- VoiceConfig ----------


def test_voice_config_defaults():
    cfg = default_voice_config()
    assert cfg.voice == "en-US-AriaNeural"
    assert cfg.rate == "-15%"


def test_voice_config_rate_format():
    with pytest.raises(ValidationError):
        VoiceConfig(voice="en-US-AriaNeural", rate="slow")


def test_voice_config_rate_outside_band():
    with pytest.raises(ValidationError):
        VoiceConfig(voice="en-US-AriaNeural", rate="-50%")
    with pytest.raises(ValidationError):
        VoiceConfig(voice="en-US-AriaNeural", rate="+30%")


def test_voice_config_pitch_format():
    with pytest.raises(ValidationError):
        VoiceConfig(voice="en-US-AriaNeural", pitch="up")


def test_voice_config_round_trip(tmp_path: Path):
    cfg = VoiceConfig(
        voice="en-US-JennyNeural",
        rate="-10%",
        pitch="+0Hz",
        pauses=[{"after_beat": "hook", "duration_ms": 800}],
    )
    p = tmp_path / "voice.yaml"
    write_voice_config(cfg, p)
    cfg2 = load_voice_config(p)
    assert cfg2 == cfg


# ---------- SeoMeta ----------


def _good_seo() -> dict:
    return {
        "title": "AI is everywhere - what older adults should know",
        "description": (
            "A calm, four-minute introduction to the AI you already use - "
            "in your search, your inbox, and your phone."
        ),
        "tags": ["ai for seniors", "geragogy", "older adults"],
        "chapters": [
            {"start_seconds": 0.0, "title": "Introduction"},
            {"start_seconds": 30.0, "title": "Where AI hides"},
            {"start_seconds": 240.0, "title": "Recap"},
        ],
        "visibility": "unlisted",
    }


def test_seo_accepts_valid():
    m = SeoMeta.model_validate(_good_seo())
    assert m.title.startswith("AI is everywhere")
    assert len(m.chapters) == 3


def test_seo_rejects_long_title():
    bad = _good_seo() | {"title": "x" * 71}
    with pytest.raises(ValidationError):
        SeoMeta.model_validate(bad)


def test_seo_rejects_chapter_not_starting_at_zero():
    bad = _good_seo()
    bad["chapters"][0] = {"start_seconds": 5.0, "title": "Late start"}
    with pytest.raises(ValidationError):
        SeoMeta.model_validate(bad)


def test_seo_rejects_non_monotonic_chapters():
    bad = _good_seo()
    bad["chapters"] = [
        {"start_seconds": 0.0, "title": "A"},
        {"start_seconds": 60.0, "title": "B"},
        {"start_seconds": 30.0, "title": "C"},
    ]
    with pytest.raises(ValidationError):
        SeoMeta.model_validate(bad)


def test_seo_rejects_tag_with_comma():
    bad = _good_seo() | {"tags": ["good tag", "bad,tag"]}
    with pytest.raises(ValidationError):
        SeoMeta.model_validate(bad)


def test_seo_round_trip(tmp_path: Path):
    m = SeoMeta(
        title="A perfectly fine title for an episode",
        description="A description that is at least forty characters long for the test.",
        tags=["one", "two"],
        chapters=[Chapter(start_seconds=0.0, title="Intro")],
    )
    p = tmp_path / "seo.yaml"
    write_seo_meta(m, p)
    m2 = load_seo_meta(p)
    assert m2 == m
