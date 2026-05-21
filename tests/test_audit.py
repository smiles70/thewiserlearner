"""Tests for `pipeline.audit`.

These tests build small in-memory scripts and confirm the auditor reaches
the expected verdicts. They cover the deterministic checks only; the
[agent] checks are exercised separately when the agent runner ships.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from pipeline import audit


@pytest.fixture
def write_script(tmp_path: Path):
    def _write(content: str) -> Path:
        p = tmp_path / "script.md"
        p.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
        return p

    return _write


GOOD_SCRIPT = """
---
id: E-001
title: "Test"
target_runtime_seconds: 240
target_wpm: 115
ai_episode: true
mynaani_mention: true
cta_subscribe: true
risk_topics: [none]
verified_claims: []
beats:
  hook: |
    Today we will use Claude to draft a short note to a grandchild. Five minutes.
  acknowledge: |
    You may be wondering if it will sound like you. We will make sure it does.
  why: |
    Knowing how to do this saves time and keeps your voice in the message.
  show: |
    I open Claude and type a single sentence describing what I want to say.
  walkthrough:
    - "Step one. Open the Claude application on your phone."
    - "Step two. Type one sentence about what you want to say."
    - "Step three. Read the draft, then ask Claude to adjust the tone."
    - "Step four. Copy the result into your messages app."
  recover: |
    If Claude misunderstands, type back: please make it warmer and shorter.
    It will rewrite. You can keep nudging it until the wording is yours.
    This is the conversation, not a single magic prompt.
  recap: |
    If you have followed along, you have now drafted a short note with Claude.
  outro: |
    If you would like a guided course, Mynaani is one route. Next episode is free.
---
"""


BAD_FORBIDDEN_SCRIPT = GOOD_SCRIPT.replace(
    "You may be wondering if it will sound like you. We will make sure it does.",
    "If you struggle with technology, don't worry, anyone can do this.",
)


def test_good_script_passes(write_script):
    p = write_script(GOOD_SCRIPT)
    report = audit.audit_script(p)
    assert report.verdict == "pass", _diagnose(report)


def test_forbidden_phrases_fail(write_script):
    p = write_script(BAD_FORBIDDEN_SCRIPT)
    report = audit.audit_script(p)
    assert report.verdict == "fail"
    failed_clauses = {c.clause for c in report.checks if c.status == "fail"}
    assert {"C-4.2", "C-4.4"} <= failed_clauses


def test_missing_beat_fails(write_script):
    bad = GOOD_SCRIPT.replace(
        "  recap: |\n    If you have followed along, you have now drafted a short note with Claude.\n",
        "",
    )
    p = write_script(bad)
    report = audit.audit_script(p)
    assert report.verdict == "fail"
    assert any(c.id == "A-1.2" and c.status == "fail" for c in report.checks)


def test_wpm_over_limit_fails(write_script):
    fast = GOOD_SCRIPT.replace("target_runtime_seconds: 240", "target_runtime_seconds: 60")
    p = write_script(fast)
    report = audit.audit_script(p)
    assert report.verdict == "fail"
    assert any(c.id == "A-3.1" and c.status == "fail" for c in report.checks)


def test_mynaani_outside_outro_fails(write_script):
    bad = GOOD_SCRIPT.replace(
        "Knowing how to do this saves time and keeps your voice in the message.",
        "Mynaani is a great course you should buy now and use today.",
    )
    p = write_script(bad)
    report = audit.audit_script(p)
    assert report.verdict == "fail"
    # Either A-9.1 (>1 mention) or A-9.2 (outside outro) must fire
    fired = {c.id for c in report.checks if c.status == "fail"}
    assert "A-9.2" in fired or "A-9.1" in fired


def test_patented_word_fails(write_script):
    bad = GOOD_SCRIPT.replace(
        "If you would like a guided course, Mynaani is one route. Next episode is free.",
        "Mynaani uses our patented method.",
    )
    p = write_script(bad)
    report = audit.audit_script(p)
    assert any(c.id == "A-9.5" and c.status == "fail" for c in report.checks)


def test_named_win_missing_fails(write_script):
    bad = GOOD_SCRIPT.replace(
        "If you have followed along, you have now drafted a short note with Claude.",
        "That was the demonstration. Thank you for watching.",
    )
    p = write_script(bad)
    report = audit.audit_script(p)
    assert any(c.id == "A-3.5" and c.status == "fail" for c in report.checks)


def test_short_recovery_in_ai_episode_fails(write_script):
    bad = GOOD_SCRIPT.replace(
        "If Claude misunderstands, type back: please make it warmer and shorter.\n"
        "    It will rewrite. You can keep nudging it until the wording is yours.\n"
        "    This is the conversation, not a single magic prompt.",
        "Just try again.",
    )
    p = write_script(bad)
    report = audit.audit_script(p)
    assert any(c.id == "A-3.6" and c.status == "fail" for c in report.checks)


def _diagnose(report) -> str:
    return "\n".join(
        f"  {c.id} ({c.clause}) {c.status}: {c.evidence}"
        for c in report.checks
        if c.status != "pass"
    )
