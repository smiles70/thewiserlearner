"""Tests for the agent adapter functions in pipeline.agents_run.

All tests run with AGENT_RUNNER_MOCK=1 (set via monkeypatch). Each test
asserts the adapter passes the right input shape through and validates the
canned mock response against the agent's output schema.
"""

from __future__ import annotations

import pytest

from pipeline.agent_runner import AgentRunError
from pipeline.agents_run import (
    AnalystProposal,
    AuditorAgentReport,
    CaptionerReport,
    PublisherVerdict,
    ResearcherReport,
    ScripterOutput,
    run_analyst,
    run_auditor_subjective,
    run_captioner_verify,
    run_publisher,
    run_researcher,
    run_scripter,
    run_seo,
    run_visual_director,
    run_voice_director,
)
from pipeline.seo_meta import SeoMeta
from pipeline.storyboard import Composition
from pipeline.voice_config import VoiceConfig


@pytest.fixture(autouse=True)
def _mock_mode(monkeypatch):
    monkeypatch.setenv("AGENT_RUNNER_MOCK", "1")


# ---------- visual director ----------


def _full_composition_mock() -> dict:
    """Build a minimum-valid Composition dict (all 8 beats in order)."""
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
        beat = {
            "beat": name,
            "image_prompt": f"calm domestic scene for {name}, no faces, no text",
            "title": name.title(),
            "title_font_px": 96,
            "body_font_px": 56,
            "contrast_ratio": 8.0,
            "dwell_seconds": 5.0,
        }
        if name == "walkthrough":
            beat["steps"] = [
                {"index": 1, "text": "Open the app.", "dwell_seconds": 4.0},
                {"index": 2, "text": "Tap the icon.", "dwell_seconds": 4.0},
            ]
        beats.append(beat)
    return {
        "format": "16x9",
        "fps": 25,
        "visual_theme": {
            "palette": "warm-neutral-morning-light",
            "mood": "calm-morning-light",
        },
        "transitions": {"default_ms": 500},
        "beats": beats,
    }


def test_run_visual_director_returns_composition():
    out = run_visual_director(
        script_text="...",
        voice_timings={},
        mock_response=_full_composition_mock(),
    )
    assert isinstance(out, Composition)
    assert len(out.beats) == 8


# ---------- voice director ----------


def test_run_voice_director_returns_voice_config():
    out = run_voice_director(
        script_text="hello",
        mock_response={
            "engine": "edge-tts",
            "voice": "en-US-JennyNeural",
            "rate": "-10%",
            "pitch": "+0Hz",
            "pauses": [{"after_beat": "hook", "duration_ms": 800}],
        },
    )
    assert isinstance(out, VoiceConfig)
    assert out.voice == "en-US-JennyNeural"
    assert out.rate == "-10%"


def test_run_voice_director_invalid_rate_band_rejected():
    with pytest.raises(AgentRunError):
        run_voice_director(
            script_text="hi",
            mock_response={
                "engine": "edge-tts",
                "voice": "en-US-AriaNeural",
                "rate": "-50%",  # outside contract-safe band
                "pitch": "+0Hz",
            },
        )


# ---------- scripter ----------


def test_run_scripter_returns_script_output():
    out = run_scripter(
        brief={"id": "E-099", "topic": "test"},
        library_entries=["L-001 ..."],
        contract_excerpt="C-1.1 ...",
        mock_response={
            "front_matter": {"id": "E-099-test", "title": "Test"},
            "body_markdown": "# Hook\n\n" + ("Word " * 60),
        },
    )
    assert isinstance(out, ScripterOutput)
    assert out.front_matter["id"] == "E-099-test"


def test_run_scripter_rejects_short_body():
    with pytest.raises(AgentRunError):
        run_scripter(
            brief={},
            library_entries=[],
            contract_excerpt="",
            mock_response={"front_matter": {}, "body_markdown": "too short"},
        )


# ---------- seo ----------


def test_run_seo_returns_seo_meta():
    out = run_seo(
        script_text="...",
        mock_response={
            "title": "AI is everywhere - what to know",
            "description": "x" * 50,
            "tags": ["ai for seniors", "geragogy"],
            "chapters": [{"start_seconds": 0.0, "title": "Intro"}],
        },
    )
    assert isinstance(out, SeoMeta)
    assert out.title.startswith("AI is everywhere")


# ---------- auditor (subjective) ----------


def test_run_auditor_returns_report():
    out = run_auditor_subjective(
        script_text="...",
        contract_text="...",
        audit_rubric_text="...",
        mock_response={
            "checks": [
                {"clause": "C-2.1", "status": "pass", "rationale": "tone is calm"},
                {"clause": "C-2.2", "status": "pass", "rationale": "no urgency"},
            ],
            "overall": "pass",
        },
    )
    assert isinstance(out, AuditorAgentReport)
    assert out.overall == "pass"
    assert len(out.checks) == 2


def test_run_auditor_rejects_bad_clause_format():
    with pytest.raises(AgentRunError):
        run_auditor_subjective(
            script_text="",
            contract_text="",
            audit_rubric_text="",
            mock_response={
                "checks": [{"clause": "Bad", "status": "pass", "rationale": "x"}],
                "overall": "pass",
            },
        )


# ---------- captioner ----------


def test_run_captioner_returns_report():
    out = run_captioner_verify(
        captions_srt="1\n00:00:00,000 --> 00:00:02,000\nHello.\n",
        script_text="...",
        contract_c7_excerpt="...",
        mock_response={
            "checks": [
                {"clause": "C-7.1", "status": "pass", "rationale": "verbatim"},
                {"clause": "C-7.2", "status": "pass", "rationale": "readable"},
            ],
            "overall": "pass",
        },
    )
    assert isinstance(out, CaptionerReport)
    assert out.checks[0].clause == "C-7.1"


def test_run_captioner_rejects_non_c7_clause():
    with pytest.raises(AgentRunError):
        run_captioner_verify(
            captions_srt="",
            script_text="",
            contract_c7_excerpt="",
            mock_response={
                "checks": [
                    {"clause": "C-3.4", "status": "pass", "rationale": "x"}
                ],  # not C-7
                "overall": "pass",
            },
        )


# ---------- analyst ----------


# ---------- researcher ----------


def test_run_researcher_returns_candidates():
    out = run_researcher(
        brief={"id": "E-099", "topic": "older adults using AI assistants"},
        existing_library_ids=["L-001-knowles-2020"],
        mock_response={
            "candidates": [
                {
                    "proposed_id": "L-020-czaja-2025-llm-elders",
                    "title": "Older adults and large language models",
                    "authors": ["Czaja, S."],
                    "year": 2025,
                    "doi": "10.1234/xyz",
                    "relevance": "Directly studies the target audience adopting LLM assistants.",
                }
            ]
        },
    )
    assert isinstance(out, ResearcherReport)
    assert out.candidates[0].proposed_id.startswith("L-")


def test_run_researcher_rejects_bad_id():
    with pytest.raises(AgentRunError):
        run_researcher(
            brief={},
            existing_library_ids=[],
            mock_response={
                "candidates": [
                    {
                        "proposed_id": "X-999-bogus",
                        "title": "x",
                        "authors": ["A"],
                        "year": 2020,
                        "relevance": "bogus citation format",
                    }
                ]
            },
        )


# ---------- publisher ----------


def test_run_publisher_returns_verdict():
    out = run_publisher(
        audit_json={"verdict": "pass"},
        seo_meta={"title": "x", "description": "y"},
        captioner_verdict={"overall": "pass"},
        mock_response={
            "decision": "publish",
            "rationale": "Audit and captioner both passed; SEO is contract-compliant.",
            "visibility_override": "unlisted",
        },
    )
    assert isinstance(out, PublisherVerdict)
    assert out.decision == "publish"
    assert out.visibility_override == "unlisted"


def test_run_publisher_can_hold():
    out = run_publisher(
        audit_json={"verdict": "pass"},
        seo_meta={"title": "x"},
        mock_response={
            "decision": "hold",
            "rationale": "Captioner verdict missing; refuse to publish without C-7 sign-off.",
        },
    )
    assert out.decision == "hold"
    assert out.visibility_override is None


# ---------- analyst ----------


def test_run_analyst_returns_proposal():
    out = run_analyst(
        recent_metrics=[{"video_id": "abc", "view_count": 100}],
        contract_text="C-5.2 ...",
        mock_response={
            "summary": (
                "After three episodes, average view duration is 205s of 300s. "
                "Watch-through is acceptable; CTAs in outro under-perform."
            ),
            "adr_markdown": "# ADR-0002\n\n" + ("body " * 50),
            "contract_clauses_affected": ["C-9.3"],
        },
    )
    assert isinstance(out, AnalystProposal)
    assert "C-9.3" in out.contract_clauses_affected
