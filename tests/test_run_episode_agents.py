"""Tests for the agent-stage hooks in pipeline.run_episode.

Exercises the no-op behaviour when agents are disabled (status quo), and the
mock-driven behaviour when --with-agents is set (RUN_EPISODE_AGENTS=1) with
canned responses in `<episode>/_mocks/*.json`.

We do NOT run TTS, captions, visuals, or composite here — those have their
own tests. We invoke the private hook helpers directly so we can verify the
artefacts they produce without spinning up the whole pipeline.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipeline import run_episode as rep


@pytest.fixture
def script(tmp_path: Path) -> Path:
    p = tmp_path / "script.md"
    p.write_text("# hook\n\nHello.\n", encoding="utf-8")
    return p


# ---------- _agents_enabled / _load_mock ----------


def test_agents_disabled_by_default(monkeypatch):
    monkeypatch.delenv("RUN_EPISODE_AGENTS", raising=False)
    assert rep._agents_enabled() is False


def test_agents_enabled_when_env_set(monkeypatch):
    monkeypatch.setenv("RUN_EPISODE_AGENTS", "1")
    assert rep._agents_enabled() is True


def test_load_mock_returns_none_when_missing(tmp_path: Path):
    assert rep._load_mock(tmp_path, "voice-director") is None


def test_load_mock_parses_existing_file(tmp_path: Path):
    mocks = tmp_path / rep.MOCKS_DIRNAME
    mocks.mkdir()
    (mocks / "voice-director.json").write_text(json.dumps({"a": 1}), encoding="utf-8")
    assert rep._load_mock(tmp_path, "voice-director") == {"a": 1}


# ---------- voice-director hook ----------


def test_voice_director_no_op_when_disabled(script: Path, monkeypatch):
    monkeypatch.delenv("RUN_EPISODE_AGENTS", raising=False)
    rep._maybe_run_voice_director(script, script.parent)
    assert not (script.parent / rep.VOICE_YAML).exists()


def test_voice_director_writes_yaml_in_mock_mode(script: Path, monkeypatch):
    monkeypatch.setenv("RUN_EPISODE_AGENTS", "1")
    monkeypatch.setenv("AGENT_RUNNER_MOCK", "1")
    mocks = script.parent / rep.MOCKS_DIRNAME
    mocks.mkdir()
    (mocks / "voice-director.json").write_text(
        json.dumps(
            {
                "engine": "edge-tts",
                "voice": "en-US-JennyNeural",
                "rate": "-12%",
                "pitch": "+0Hz",
                "pauses": [],
            }
        ),
        encoding="utf-8",
    )
    rep._maybe_run_voice_director(script, script.parent)
    voice_yaml = script.parent / rep.VOICE_YAML
    assert voice_yaml.is_file()
    text = voice_yaml.read_text(encoding="utf-8")
    assert "JennyNeural" in text
    assert "-12%" in text


def test_voice_director_idempotent_when_already_present(script: Path, monkeypatch):
    monkeypatch.setenv("RUN_EPISODE_AGENTS", "1")
    monkeypatch.setenv("AGENT_RUNNER_MOCK", "1")
    existing = script.parent / rep.VOICE_YAML
    existing.write_text("voice: en-US-AriaNeural\nrate: '+0%'\npitch: '+0Hz'\n", encoding="utf-8")
    # No _mocks dir; would crash if it tried to run.
    rep._maybe_run_voice_director(script, script.parent)
    assert existing.read_text(encoding="utf-8").startswith("voice: en-US-AriaNeural")


# ---------- _voice_kwargs_from_yaml ----------


def test_voice_kwargs_empty_when_no_yaml(tmp_path: Path):
    assert rep._voice_kwargs_from_yaml(tmp_path) == {}


def test_voice_kwargs_loaded_from_yaml(tmp_path: Path):
    (tmp_path / rep.VOICE_YAML).write_text(
        "engine: edge-tts\nvoice: en-US-JennyNeural\nrate: '-12%'\npitch: '+0Hz'\n",
        encoding="utf-8",
    )
    kwargs = rep._voice_kwargs_from_yaml(tmp_path)
    assert kwargs == {"voice": "en-US-JennyNeural", "rate": "-12%", "pitch": "+0Hz"}


# ---------- seo hook ----------


def test_seo_writes_yaml_in_mock_mode(script: Path, monkeypatch):
    monkeypatch.setenv("RUN_EPISODE_AGENTS", "1")
    monkeypatch.setenv("AGENT_RUNNER_MOCK", "1")
    mocks = script.parent / rep.MOCKS_DIRNAME
    mocks.mkdir()
    (mocks / "seo.json").write_text(
        json.dumps(
            {
                "title": "AI is everywhere - what to know",
                "description": "x" * 60,
                "tags": ["ai for seniors"],
                "chapters": [{"start_seconds": 0.0, "title": "Intro"}],
                "visibility": "unlisted",
            }
        ),
        encoding="utf-8",
    )
    rep._maybe_run_seo(script, script.parent)
    seo_yaml = script.parent / rep.SEO_YAML
    assert seo_yaml.is_file()
    assert "AI is everywhere" in seo_yaml.read_text(encoding="utf-8")


# ---------- visual-director hook ----------


def _composition_mock_dict() -> dict:
    beats = []
    for name in (
        "hook",
        "acknowledge",
        "why",
        "show",
        "walkthrough",
        "recover",
        "recap",
        "outro",
    ):
        b = {
            "beat": name,
            "image_prompt": f"calm scene for {name}",
            "title": name.title(),
            "title_font_px": 96,
            "body_font_px": 56,
            "contrast_ratio": 8.0,
            "dwell_seconds": 5.0,
        }
        if name == "walkthrough":
            b["steps"] = [
                {"index": 1, "text": "Open it.", "dwell_seconds": 4.0},
                {"index": 2, "text": "Tap save.", "dwell_seconds": 4.0},
            ]
        beats.append(b)
    return {
        "format": "16x9",
        "fps": 25,
        "visual_theme": {"palette": "warm-neutral-morning-light", "mood": "calm"},
        "transitions": {"default_ms": 500},
        "beats": beats,
    }


def test_visual_director_writes_composition_in_mock_mode(script: Path, monkeypatch):
    monkeypatch.setenv("RUN_EPISODE_AGENTS", "1")
    monkeypatch.setenv("AGENT_RUNNER_MOCK", "1")
    mocks = script.parent / rep.MOCKS_DIRNAME
    mocks.mkdir()
    (mocks / "visual-director.json").write_text(
        json.dumps(_composition_mock_dict()),
        encoding="utf-8",
    )
    voice_json = script.parent / "voice.json"
    voice_json.write_text(json.dumps({"beats": []}), encoding="utf-8")
    rep._maybe_run_visual_director(script, voice_json, script.parent)
    comp_yaml = script.parent / rep.COMPOSITION_YAML
    assert comp_yaml.is_file()
    text = comp_yaml.read_text(encoding="utf-8")
    assert "walkthrough" in text
    assert "warm-neutral-morning-light" in text
