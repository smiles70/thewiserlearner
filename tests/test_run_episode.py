"""Tests for `pipeline.run_episode` orchestrator (audit-stage gating)."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from pipeline import run_episode

GOOD_SCRIPT = """\
---
id: E-TEST
title: "Test"
target_runtime_seconds: 240
target_wpm: 110
ai_episode: false
mynaani_mention: false
cta_subscribe: true
risk_topics: [none]
verified_claims: []
beats:
  hook: "A short hook line for the test."
  acknowledge: "A short acknowledgement line for the test."
  why: "A short reason line for the test."
  show: "A short demonstration narration line for the test."
  walkthrough:
    - "Part one. The first numbered step."
    - "Part two. The second numbered step."
  recover: "A short recovery line for the test."
  recap: "If you have followed along, you have now seen the test."
  outro: "Thank you for following along with the test."
---
"""

BAD_SCRIPT = GOOD_SCRIPT.replace(
    "A short reason line for the test.",
    "If you struggle with technology, don't worry, anyone can do this.",
)


@pytest.fixture
def script(tmp_path: Path):
    def _w(text: str) -> Path:
        d = tmp_path / "E-TEST"
        d.mkdir()
        p = d / "script.md"
        p.write_text(textwrap.dedent(text).lstrip(), encoding="utf-8")
        return p

    return _w


def test_unknown_stage_returns_2(script):
    rc = run_episode.run(script(GOOD_SCRIPT), from_stage="bogus")
    assert rc == 2


def test_missing_script_returns_2(tmp_path: Path):
    rc = run_episode.run(tmp_path / "no-such.md")
    assert rc == 2


def test_failing_audit_blocks_pipeline(script, capsys):
    rc = run_episode.run(script(BAD_SCRIPT))
    out = capsys.readouterr()
    assert rc == 1
    assert "BLOCKED" in out.err


def test_resume_from_composite_requires_existing_voice_wav(script, capsys):
    rc = run_episode.run(script(GOOD_SCRIPT), from_stage="composite")
    out = capsys.readouterr()
    assert rc == 2
    assert "voice.wav" in out.err


def test_stages_constant_is_canonical_order():
    assert run_episode.STAGES == ("audit", "tts", "captions", "visuals", "composite")
