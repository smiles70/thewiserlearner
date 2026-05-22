"""Tests for agent_runner. Live mode is not exercised here (no network)."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import BaseModel, Field

from pipeline.agent_runner import (
    AgentRunError,
    _extract_json,
    compose_system_prompt,
    compose_user_message,
    load_agent,
    load_skill,
    run_agent,
)


class Result(BaseModel):
    name: str = Field(min_length=2)
    score: int = Field(ge=0, le=100)


# ---------- spec loading ----------


def test_load_agent_returns_frontmatter_and_body():
    spec = load_agent("scripter")
    assert spec.role == "scripter"
    assert spec.front_matter.get("role") == "scripter"
    assert "C-1.*" in str(spec.front_matter.get("contract_clauses", []))
    assert "Scripter agent" in spec.body or "scripter" in spec.body.lower()


def test_load_agent_missing_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_agent("does-not-exist", agents_dir=tmp_path)


def test_load_skill_known():
    s = load_skill("contract-audit")
    assert s.name == "contract-audit"
    assert s.front_matter.get("name") == "contract-audit"


# ---------- prompt composition ----------


def test_compose_system_prompt_includes_skill():
    agent = load_agent("auditor")
    skill = load_skill("contract-audit")
    sp = compose_system_prompt(agent, [skill])
    assert "SKILL: contract-audit" in sp
    assert agent.body.split("\n")[0] in sp


def test_compose_user_message_includes_schema_and_inputs():
    msg = compose_user_message({"foo": "bar"}, Result)
    assert "foo" in msg
    assert "score" in msg
    assert "schema" in msg.lower()


# ---------- mock-mode behaviour ----------


def test_run_agent_mock_returns_validated_object(monkeypatch):
    monkeypatch.setenv("AGENT_RUNNER_MOCK", "1")
    out = run_agent(
        agent_role="auditor",
        skill_names=["contract-audit"],
        inputs={"script": "..."},
        output_schema=Result,
        mock_response={"name": "ok", "score": 80},
    )
    assert isinstance(out, Result)
    assert out.name == "ok"
    assert out.score == 80


def test_run_agent_mock_via_inputs_key(monkeypatch):
    monkeypatch.setenv("AGENT_RUNNER_MOCK", "1")
    out = run_agent(
        agent_role="auditor",
        inputs={"__mock_response__": {"name": "via-input", "score": 50}},
        output_schema=Result,
    )
    assert out.name == "via-input"


def test_run_agent_mock_without_response_raises(monkeypatch):
    monkeypatch.setenv("AGENT_RUNNER_MOCK", "1")
    with pytest.raises(AgentRunError, match="no mock_response"):
        run_agent(
            agent_role="auditor",
            inputs={"x": 1},
            output_schema=Result,
        )


def test_run_agent_mock_validation_failure(monkeypatch):
    monkeypatch.setenv("AGENT_RUNNER_MOCK", "1")
    with pytest.raises(AgentRunError, match="failed schema validation"):
        run_agent(
            agent_role="auditor",
            inputs={},
            output_schema=Result,
            mock_response={"name": "x", "score": 999},  # score out of band
        )


def test_run_agent_live_without_key_raises(monkeypatch):
    # AGENT_RUNNER_MOCK not set, no API key, no mock response -> error
    monkeypatch.delenv("AGENT_RUNNER_MOCK", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(AgentRunError, match="ANTHROPIC_API_KEY"):
        run_agent(
            agent_role="auditor",
            inputs={"x": 1},
            output_schema=Result,
        )


# ---------- json extraction ----------


def test_extract_json_handles_plain_object():
    assert _extract_json('{"a":1}') == '{"a":1}'


def test_extract_json_strips_json_fence():
    assert _extract_json('```json\n{"a":1}\n```') == '{"a":1}'


def test_extract_json_strips_bare_fence():
    assert _extract_json('```\n{"a":1}\n```') == '{"a":1}'
