"""Thin Python adapters that invoke each Claude agent.

Every function in this module:
  - composes the structured inputs the agent needs (script, library refs,
    contract excerpts, timings, etc.)
  - hands them to `pipeline.agent_runner.run_agent` with the correct
    output schema and optional skill attachments
  - returns the validated pydantic object

File I/O is the caller's responsibility (typically `run_episode`). These
adapters do not read or write disk so they are easy to unit-test in mock
mode without fixtures.

Mock mode (env `AGENT_RUNNER_MOCK=1` or `mock_response=` kwarg) is the
default for tests and CI. Live mode requires `ANTHROPIC_API_KEY`.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from pipeline.agent_runner import run_agent
from pipeline.cost_guard import CostGuard
from pipeline.seo_meta import SeoMeta
from pipeline.storyboard import Composition
from pipeline.voice_config import VoiceConfig

# ---------------------------------------------------------------------------
# Output schemas (only those not already defined in dedicated modules)
# ---------------------------------------------------------------------------


class ScripterOutput(BaseModel):
    """What the scripter agent returns: front matter + markdown body."""

    front_matter: dict[str, Any]
    body_markdown: str = Field(min_length=200)


class AuditorCheckVerdict(BaseModel):
    clause: str = Field(pattern=r"^C-\d+\.\d+[a-z]?$")
    status: str = Field(pattern=r"^(pass|fail|unsure)$")
    rationale: str = Field(min_length=4, max_length=400)


class AuditorAgentReport(BaseModel):
    checks: list[AuditorCheckVerdict] = Field(min_length=1)
    overall: str = Field(pattern=r"^(pass|fail|unsure)$")


class CaptionerCheckVerdict(BaseModel):
    clause: str = Field(pattern=r"^C-7\.\d+$")
    status: str = Field(pattern=r"^(pass|fail|unsure)$")
    rationale: str = Field(min_length=4, max_length=400)


class CaptionerReport(BaseModel):
    checks: list[CaptionerCheckVerdict] = Field(min_length=1)
    overall: str = Field(pattern=r"^(pass|fail|unsure)$")


class AnalystProposal(BaseModel):
    summary: str = Field(min_length=40, max_length=800)
    adr_markdown: str = Field(min_length=200)
    contract_clauses_affected: list[str] = Field(default_factory=list)


class ResearcherCandidate(BaseModel):
    proposed_id: str = Field(pattern=r"^L-\d{3}-[a-z0-9-]+$")
    title: str = Field(min_length=4, max_length=200)
    authors: list[str] = Field(min_length=1)
    year: int = Field(ge=1900, le=2100)
    doi: str = ""
    relevance: str = Field(min_length=10, max_length=400)


class ResearcherReport(BaseModel):
    candidates: list[ResearcherCandidate] = Field(min_length=1, max_length=15)


class PublisherVerdict(BaseModel):
    decision: str = Field(pattern=r"^(publish|hold|reject)$")
    rationale: str = Field(min_length=10, max_length=400)
    visibility_override: str | None = Field(
        default=None, pattern=r"^(public|unlisted|private)$"
    )


# ---------------------------------------------------------------------------
# Agent calls
# ---------------------------------------------------------------------------


def run_visual_director(
    *,
    script_text: str,
    voice_timings: dict[str, Any],
    cost_guard: CostGuard | None = None,
    episode_id: str = "unknown",
    mock_response: dict[str, Any] | None = None,
) -> Composition:
    """Produce a `composition.yaml`-compatible Composition."""
    return run_agent(
        agent_role="visual-director",
        skill_names=["visual-director"],
        inputs={"script": script_text, "voice_timings": voice_timings},
        output_schema=Composition,
        cost_guard=cost_guard,
        episode_id=episode_id,
        mock_response=mock_response,
    )


def run_voice_director(
    *,
    script_text: str,
    cost_guard: CostGuard | None = None,
    episode_id: str = "unknown",
    mock_response: dict[str, Any] | None = None,
) -> VoiceConfig:
    """Produce a `voice.yaml`-compatible VoiceConfig."""
    return run_agent(
        agent_role="voice-director",
        skill_names=["voice-director"],
        inputs={"script": script_text},
        output_schema=VoiceConfig,
        cost_guard=cost_guard,
        episode_id=episode_id,
        mock_response=mock_response,
    )


def run_scripter(
    *,
    brief: dict[str, Any],
    library_entries: list[str],
    contract_excerpt: str,
    cost_guard: CostGuard | None = None,
    episode_id: str = "unknown",
    mock_response: dict[str, Any] | None = None,
) -> ScripterOutput:
    """Draft an 8-beat script from a brief + cited library entries."""
    return run_agent(
        agent_role="scripter",
        skill_names=[],
        inputs={
            "brief": brief,
            "library_entries": library_entries,
            "contract_excerpt": contract_excerpt,
        },
        output_schema=ScripterOutput,
        cost_guard=cost_guard,
        episode_id=episode_id,
        mock_response=mock_response,
    )


def run_seo(
    *,
    script_text: str,
    cost_guard: CostGuard | None = None,
    episode_id: str = "unknown",
    mock_response: dict[str, Any] | None = None,
) -> SeoMeta:
    """Author the SEO/meta object for the episode."""
    return run_agent(
        agent_role="seo",
        skill_names=["seo"],
        inputs={"script": script_text},
        output_schema=SeoMeta,
        cost_guard=cost_guard,
        episode_id=episode_id,
        mock_response=mock_response,
    )


def run_auditor_subjective(
    *,
    script_text: str,
    contract_text: str,
    audit_rubric_text: str,
    cost_guard: CostGuard | None = None,
    episode_id: str = "unknown",
    mock_response: dict[str, Any] | None = None,
) -> AuditorAgentReport:
    """Run the subjective half of the audit rubric (agent-judged clauses)."""
    return run_agent(
        agent_role="auditor",
        skill_names=["contract-audit"],
        inputs={
            "script": script_text,
            "contract": contract_text,
            "rubric": audit_rubric_text,
        },
        output_schema=AuditorAgentReport,
        cost_guard=cost_guard,
        episode_id=episode_id,
        mock_response=mock_response,
    )


def run_captioner_verify(
    *,
    captions_srt: str,
    script_text: str,
    contract_c7_excerpt: str,
    cost_guard: CostGuard | None = None,
    episode_id: str = "unknown",
    mock_response: dict[str, Any] | None = None,
) -> CaptionerReport:
    """Judge the SRT against contract clauses C-7.*."""
    return run_agent(
        agent_role="captioner",
        skill_names=["captioner"],
        inputs={
            "captions_srt": captions_srt,
            "script": script_text,
            "contract_c7": contract_c7_excerpt,
        },
        output_schema=CaptionerReport,
        cost_guard=cost_guard,
        episode_id=episode_id,
        mock_response=mock_response,
    )


def run_analyst(
    *,
    recent_metrics: list[dict[str, Any]],
    contract_text: str,
    cost_guard: CostGuard | None = None,
    episode_id: str = "unknown",
    mock_response: dict[str, Any] | None = None,
) -> AnalystProposal:
    """Read recent analytics and propose a contract amendment (ADR)."""
    return run_agent(
        agent_role="analyst",
        skill_names=["analyst"],
        inputs={"metrics": recent_metrics, "contract": contract_text},
        output_schema=AnalystProposal,
        cost_guard=cost_guard,
        episode_id=episode_id,
        mock_response=mock_response,
    )


def run_researcher(
    *,
    brief: dict[str, Any],
    existing_library_ids: list[str],
    cost_guard: CostGuard | None = None,
    episode_id: str = "unknown",
    mock_response: dict[str, Any] | None = None,
) -> ResearcherReport:
    """Propose new library candidates relevant to the brief."""
    return run_agent(
        agent_role="researcher",
        skill_names=["library-verify"],
        inputs={"brief": brief, "existing_library_ids": existing_library_ids},
        output_schema=ResearcherReport,
        cost_guard=cost_guard,
        episode_id=episode_id,
        mock_response=mock_response,
    )


def run_publisher(
    *,
    audit_json: dict[str, Any],
    seo_meta: dict[str, Any],
    captioner_verdict: dict[str, Any] | None = None,
    cost_guard: CostGuard | None = None,
    episode_id: str = "unknown",
    mock_response: dict[str, Any] | None = None,
) -> PublisherVerdict:
    """Final gate before YouTube upload: confirm audit + captions + SEO are
    all consistent and decide on visibility."""
    return run_agent(
        agent_role="publisher",
        skill_names=[],
        inputs={
            "audit": audit_json,
            "seo": seo_meta,
            "captioner": captioner_verdict or {},
        },
        output_schema=PublisherVerdict,
        cost_guard=cost_guard,
        episode_id=episode_id,
        mock_response=mock_response,
    )
