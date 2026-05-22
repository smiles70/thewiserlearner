"""Adapter that turns a markdown agent spec + skill spec into a Claude call.

Reads `agents/<role>.md` and (optionally) `skills/<name>/SKILL.md`, composes a
single system prompt, sends it to Anthropic with the supplied user inputs, and
parses the JSON response against a pydantic schema.

Mock mode
---------
If env var `AGENT_RUNNER_MOCK=1` is set OR the pydantic input contains a
`__mock_response__` key, the runner returns that canned object without making
any network call. This keeps the pipeline runnable end-to-end without an
ANTHROPIC_API_KEY for tests, CI, and offline development.

Cost
----
Every real call is run through `CostGuard.check_and_charge` using a coarse
estimate based on Anthropic's published Sonnet pricing:
    input  $3.00 / Mtok    output $15.00 / Mtok
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from pipeline.cost_guard import CostGuard

T = TypeVar("T", bound=BaseModel)

ANTHROPIC_INPUT_USD_PER_MTOK = 3.00
ANTHROPIC_OUTPUT_USD_PER_MTOK = 15.00
DEFAULT_MODEL = "claude-sonnet-4-5"

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = REPO_ROOT / "agents"
SKILLS_DIR = REPO_ROOT / "skills"


# ---------------------------------------------------------------------------
# Spec loading
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AgentSpec:
    role: str
    front_matter: dict[str, Any]
    body: str


@dataclass(frozen=True)
class SkillSpec:
    name: str
    front_matter: dict[str, Any]
    body: str


_FRONTMATTER_RE = re.compile(
    r"\A---\s*\n(?P<fm>.*?)\n---\s*\n(?P<body>.*)\Z",
    re.DOTALL,
)


def _parse_front_matter(text: str) -> tuple[dict[str, Any], str]:
    import yaml

    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fm = yaml.safe_load(m.group("fm")) or {}
    return fm, m.group("body").strip()


def load_agent(role: str, *, agents_dir: Path | None = None) -> AgentSpec:
    base = agents_dir or AGENTS_DIR
    path = base / f"{role}.md"
    if not path.is_file():
        raise FileNotFoundError(f"agent spec not found: {path}")
    fm, body = _parse_front_matter(path.read_text(encoding="utf-8"))
    return AgentSpec(role=role, front_matter=fm, body=body)


def load_skill(name: str, *, skills_dir: Path | None = None) -> SkillSpec:
    base = skills_dir or SKILLS_DIR
    path = base / name / "SKILL.md"
    if not path.is_file():
        raise FileNotFoundError(f"skill spec not found: {path}")
    fm, body = _parse_front_matter(path.read_text(encoding="utf-8"))
    return SkillSpec(name=name, front_matter=fm, body=body)


# ---------------------------------------------------------------------------
# Prompt composition
# ---------------------------------------------------------------------------


def compose_system_prompt(agent: AgentSpec, skills: list[SkillSpec]) -> str:
    parts = [agent.body.strip()]
    for skill in skills:
        parts.append(f"\n\n## SKILL: {skill.name}\n\n{skill.body.strip()}")
    return "\n".join(parts)


def compose_user_message(inputs: dict[str, Any], output_schema: type[BaseModel]) -> str:
    schema_json = json.dumps(output_schema.model_json_schema(), indent=2)
    inputs_json = json.dumps(inputs, indent=2, default=str)
    return (
        "Inputs (JSON):\n"
        f"```json\n{inputs_json}\n```\n\n"
        "Respond with a single JSON object matching this schema. "
        "No prose before or after; no markdown fences.\n\n"
        "Schema:\n"
        f"```json\n{schema_json}\n```"
    )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


class AgentRunError(RuntimeError):
    """Raised when the agent response cannot be parsed/validated after retries."""


def _is_mock_mode() -> bool:
    return os.environ.get("AGENT_RUNNER_MOCK") == "1"


def _extract_json(text: str) -> str:
    """Pull the first JSON object out of a possibly-fenced response."""
    text = text.strip()
    if text.startswith("```"):
        # strip leading fence (```json or ```)
        text = re.sub(r"\A```[a-zA-Z0-9]*\n", "", text)
        if text.endswith("```"):
            text = text[: -len("```")]
    return text.strip()


def _estimate_cost_usd(input_chars: int, output_chars: int) -> float:
    """Coarse char->token ratio of 4:1; conservative."""
    in_tok = input_chars / 4
    out_tok = output_chars / 4
    return (in_tok / 1_000_000) * ANTHROPIC_INPUT_USD_PER_MTOK + (
        out_tok / 1_000_000
    ) * ANTHROPIC_OUTPUT_USD_PER_MTOK


def run_agent(
    *,
    agent_role: str,
    skill_names: list[str] | None = None,
    inputs: dict[str, Any],
    output_schema: type[T],
    episode_id: str = "unknown",
    cost_guard: CostGuard | None = None,
    model: str = DEFAULT_MODEL,
    max_retries: int = 2,
    mock_response: dict[str, Any] | None = None,
) -> T:
    """Run one agent turn. Returns a validated instance of `output_schema`.

    In mock mode, `mock_response` (or `inputs["__mock_response__"]`) is parsed
    directly. In live mode, the Anthropic API is called and retried up to
    `max_retries` extra times on validation failure.
    """
    skills = [load_skill(name) for name in (skill_names or [])]
    agent = load_agent(agent_role)
    system_prompt = compose_system_prompt(agent, skills)
    user_message = compose_user_message(inputs, output_schema)

    canned = mock_response or inputs.get("__mock_response__")
    if _is_mock_mode() or canned is not None:
        if canned is None:
            raise AgentRunError(
                f"agent {agent_role}: AGENT_RUNNER_MOCK=1 but no mock_response supplied"
            )
        try:
            return output_schema.model_validate(canned)
        except ValidationError as exc:
            raise AgentRunError(f"mock response failed schema validation: {exc}") from exc

    return _run_live(
        system_prompt=system_prompt,
        user_message=user_message,
        output_schema=output_schema,
        episode_id=episode_id,
        cost_guard=cost_guard,
        model=model,
        max_retries=max_retries,
    )


def _run_live(
    *,
    system_prompt: str,
    user_message: str,
    output_schema: type[T],
    episode_id: str,
    cost_guard: CostGuard | None,
    model: str,
    max_retries: int,
) -> T:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise AgentRunError(
            "ANTHROPIC_API_KEY not set and AGENT_RUNNER_MOCK!=1; cannot make live call"
        )
    try:
        import anthropic
    except ImportError as exc:
        raise AgentRunError("anthropic SDK not installed (`pip install anthropic`)") from exc

    client = anthropic.Anthropic(api_key=api_key)

    messages = [{"role": "user", "content": user_message}]
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        if cost_guard is not None:
            est = _estimate_cost_usd(
                input_chars=len(system_prompt) + sum(len(m["content"]) for m in messages),
                output_chars=4000,
            )
            cost_guard.check_and_charge(
                provider="anthropic",
                amount_usd=est,
                episode_id=episode_id,
                note=f"agent={messages[0]['content'][:40]}... attempt={attempt}",
            )
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            system=system_prompt,
            messages=messages,
        )
        text_blocks = [b.text for b in response.content if getattr(b, "type", "") == "text"]
        raw = "\n".join(text_blocks)
        try:
            parsed = json.loads(_extract_json(raw))
            return output_schema.model_validate(parsed)
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = exc
            messages.append({"role": "assistant", "content": raw})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "That response failed validation: "
                        f"{exc!s}\n\nReturn ONLY a JSON object matching the schema."
                    ),
                }
            )
    raise AgentRunError(
        f"agent failed after {max_retries + 1} attempts; last error: {last_error}"
    )
