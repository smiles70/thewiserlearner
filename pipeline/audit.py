"""Contract auditor — deterministic checks against `contract/CONTRACT.md`.

This module implements the deterministic half of `contract/audit-rubric.md`.
The agent (Claude) half is invoked separately by `pipeline/run_episode.py`.

Usage:
    from pipeline.audit import audit_script
    report = audit_script(Path("episodes/E-001-hello-claude/script.md"))
    print(report.verdict)  # "pass" | "fail" | "needs-review"

CLI:
    python -m pipeline.cli audit episodes/E-001-hello-claude/script.md
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

CONTRACT_VERSION = "1.0.0-draft"
DATA_DIR = Path(__file__).parent / "data"
FORBIDDEN_PATTERNS_PATH = DATA_DIR / "forbidden_patterns.yaml"

MAX_WPM = 120
WINDOW_MAX_WPM = 125
WINDOW_SECONDS = 30
RECOVERY_MIN_WORDS = 25
MYNAANI_MAX_WORDS = 12

REQUIRED_BEATS = (
    "hook",
    "acknowledge",
    "why",
    "show",
    "walkthrough",
    "recover",
    "recap",
    "outro",
)


# --------------------------------------------------------------------------- #
# Data classes                                                                #
# --------------------------------------------------------------------------- #


@dataclass
class Check:
    id: str
    clause: str
    kind: str  # "deterministic" | "agent"
    status: str  # "pass" | "fail" | "unsure"
    evidence: str = ""
    line_numbers: list[int] = field(default_factory=list)


@dataclass
class AuditReport:
    script_id: str
    contract_version: str
    audited_at: str
    checks: list[Check] = field(default_factory=list)

    @property
    def summary(self) -> dict[str, dict[str, int]]:
        det = {"pass": 0, "fail": 0}
        agt = {"pass": 0, "fail": 0, "unsure": 0}
        for c in self.checks:
            target = det if c.kind == "deterministic" else agt
            target[c.status] = target.get(c.status, 0) + 1
        return {"deterministic": det, "agent": agt}

    @property
    def verdict(self) -> str:
        if any(c.status == "fail" for c in self.checks):
            return "fail"
        if any(c.status == "unsure" for c in self.checks):
            return "needs-review"
        return "pass"

    def to_dict(self) -> dict[str, Any]:
        return {
            "script_id": self.script_id,
            "contract_version": self.contract_version,
            "audited_at": self.audited_at,
            "summary": self.summary,
            "checks": [asdict(c) for c in self.checks],
            "verdict": self.verdict,
        }


# --------------------------------------------------------------------------- #
# Parsing                                                                     #
# --------------------------------------------------------------------------- #


_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)


class ScriptParseError(ValueError):
    """Raised when a script file cannot be parsed into front-matter + body."""


def parse_script(path: Path) -> tuple[dict[str, Any], str]:
    """Return ``(frontmatter, body)`` parsed from a script markdown file."""
    text = path.read_text(encoding="utf-8")
    m = _FRONTMATTER_RE.match(text)
    if not m:
        raise ScriptParseError(f"{path}: missing YAML front matter")
    try:
        frontmatter = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as exc:
        raise ScriptParseError(f"{path}: invalid YAML front matter: {exc}") from exc
    if not isinstance(frontmatter, dict):
        raise ScriptParseError(f"{path}: front matter must be a mapping")
    return frontmatter, m.group(2)


def load_forbidden_patterns() -> dict[str, list[str]]:
    with FORBIDDEN_PATTERNS_PATH.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise RuntimeError(f"{FORBIDDEN_PATTERNS_PATH}: expected mapping")
    return {clause: list(map(str, patterns)) for clause, patterns in data.items()}


# --------------------------------------------------------------------------- #
# Spoken-text extraction                                                      #
# --------------------------------------------------------------------------- #


def beat_text(beat_value: Any) -> str:
    """Flatten a beat value (str | list[str]) to plain spoken text."""
    if beat_value is None:
        return ""
    if isinstance(beat_value, str):
        return beat_value.strip()
    if isinstance(beat_value, list):
        return "\n".join(str(x) for x in beat_value).strip()
    return str(beat_value)


def spoken_text(beats: dict[str, Any]) -> str:
    """Concatenate all spoken beats into a single string."""
    return "\n\n".join(beat_text(beats.get(name, "")) for name in REQUIRED_BEATS)


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w[\w'-]*\b", text))


# --------------------------------------------------------------------------- #
# Individual checks                                                           #
# --------------------------------------------------------------------------- #


def check_frontmatter_present(fm: dict[str, Any]) -> Check:
    ok = bool(fm.get("id")) and bool(fm.get("beats"))
    return Check(
        id="A-1.1",
        clause="C-1",
        kind="deterministic",
        status="pass" if ok else "fail",
        evidence="front matter parsed and has id + beats" if ok else "missing id or beats",
    )


def check_beats_present(fm: dict[str, Any]) -> Check:
    beats = fm.get("beats", {}) or {}
    missing = [b for b in REQUIRED_BEATS if not beat_text(beats.get(b))]
    return Check(
        id="A-1.2",
        clause="C-3.4",
        kind="deterministic",
        status="pass" if not missing else "fail",
        evidence=("all eight beats present" if not missing else f"missing beats: {missing}"),
    )


def check_walkthrough_steps(fm: dict[str, Any]) -> Check:
    beats = fm.get("beats", {}) or {}
    walk = beats.get("walkthrough", [])
    count = len(walk) if isinstance(walk, list) else 0
    return Check(
        id="A-1.3",
        clause="C-3.4",
        kind="deterministic",
        status="pass" if count >= 2 else "fail",
        evidence=f"walkthrough has {count} steps",
    )


def check_wpm(fm: dict[str, Any]) -> Check:
    runtime = float(fm.get("target_runtime_seconds", 0) or 0)
    beats = fm.get("beats", {}) or {}
    words = word_count(spoken_text(beats))
    if runtime <= 0:
        return Check(
            id="A-3.1",
            clause="C-3.2",
            kind="deterministic",
            status="fail",
            evidence="target_runtime_seconds missing or non-positive",
        )
    wpm = words * 60.0 / runtime
    return Check(
        id="A-3.1",
        clause="C-3.2",
        kind="deterministic",
        status="pass" if wpm <= MAX_WPM else "fail",
        evidence=f"computed wpm = {wpm:.1f} (limit {MAX_WPM})",
    )


def check_window_wpm(fm: dict[str, Any]) -> Check:
    """Coarse window scan: bucket beats by relative budget and check each."""
    runtime = float(fm.get("target_runtime_seconds", 0) or 0)
    beats = fm.get("beats", {}) or {}
    if runtime <= 0:
        return Check(
            id="A-3.2",
            clause="C-4.11",
            kind="deterministic",
            status="fail",
            evidence="cannot compute window without runtime",
        )
    text = spoken_text(beats)
    total_words = word_count(text)
    if total_words == 0:
        return Check(
            id="A-3.2",
            clause="C-4.11",
            kind="deterministic",
            status="fail",
            evidence="no spoken words",
        )
    # Approximate: words per 30 s window assuming uniform rate equals 0.5 * wpm.
    # If overall wpm <= limit, no window can exceed (without a full timing pass).
    # Producers will refine via per-line timing in pipeline/captions.py later.
    overall_wpm = total_words * 60.0 / runtime
    status = "pass" if overall_wpm <= WINDOW_MAX_WPM else "fail"
    return Check(
        id="A-3.2",
        clause="C-4.11",
        kind="deterministic",
        status=status,
        evidence=(
            f"overall wpm = {overall_wpm:.1f}; window check uses uniform-rate proxy "
            f"(refined after TTS timing pass)"
        ),
    )


def check_beat_order(fm: dict[str, Any]) -> Check:
    beats = fm.get("beats", {}) or {}
    keys = list(beats.keys()) if isinstance(beats, dict) else []
    expected = list(REQUIRED_BEATS)
    in_order = [k for k in keys if k in expected]
    ok = in_order == expected[: len(in_order)]
    return Check(
        id="A-3.4",
        clause="C-3.4",
        kind="deterministic",
        status="pass" if ok else "fail",
        evidence=f"beat order: {in_order}",
    )


_NAMED_WIN_PATTERNS = (
    r"\byou have now\b",
    r"\byou just\b.{0,40}\b(did|learned|asked|sent|set|made)\b",
    r"\bif you followed\b",
    r"\byou (?:just )?(?:successfully|now know how to)\b",
)


def check_named_win(fm: dict[str, Any]) -> Check:
    recap = beat_text((fm.get("beats", {}) or {}).get("recap", "")).lower()
    matched = any(re.search(p, recap) for p in _NAMED_WIN_PATTERNS)
    return Check(
        id="A-3.5",
        clause="C-3.4",
        kind="deterministic",
        status="pass" if matched else "fail",
        evidence="recap names a viewer-attributable win"
        if matched
        else "recap lacks a named-win phrase",
    )


def check_recovery_substance(fm: dict[str, Any]) -> Check:
    if not bool(fm.get("ai_episode")):
        return Check(
            id="A-3.6",
            clause="C-8.2",
            kind="deterministic",
            status="pass",
            evidence="not an ai_episode; recovery substance not required",
        )
    recover = beat_text((fm.get("beats", {}) or {}).get("recover", ""))
    words = word_count(recover)
    return Check(
        id="A-3.6",
        clause="C-8.2",
        kind="deterministic",
        status="pass" if words >= RECOVERY_MIN_WORDS else "fail",
        evidence=f"recover beat has {words} words (min {RECOVERY_MIN_WORDS})",
    )


def check_forbidden_patterns(fm: dict[str, Any]) -> list[Check]:
    patterns = load_forbidden_patterns()
    text = spoken_text(fm.get("beats", {}) or {}).lower()
    checks: list[Check] = []
    for clause, phrases in patterns.items():
        hits = [p for p in phrases if p.lower() in text]
        checks.append(
            Check(
                id=f"A-{clause[2:]}",
                clause=clause,
                kind="deterministic",
                status="pass" if not hits else "fail",
                evidence=("clean" if not hits else f"matched forbidden phrases: {hits}"),
            )
        )
    return checks


def check_mynaani_rules(fm: dict[str, Any]) -> list[Check]:
    beats = fm.get("beats", {}) or {}
    outro = beat_text(beats.get("outro", ""))
    full = spoken_text(beats)
    mentions_outside = re.findall(r"\bmynaani\b", full, flags=re.IGNORECASE)
    mentions_in_outro = re.findall(r"\bmynaani\b", outro, flags=re.IGNORECASE)

    out: list[Check] = []
    # A-9.1: at most one Mynaani mention anywhere
    out.append(
        Check(
            id="A-9.1",
            clause="C-9.1",
            kind="deterministic",
            status="pass" if len(mentions_outside) <= 1 else "fail",
            evidence=f"mynaani mentions = {len(mentions_outside)}",
        )
    )
    # A-9.2: Mynaani only in outro
    out_only = len(mentions_outside) == len(mentions_in_outro)
    out.append(
        Check(
            id="A-9.2",
            clause="C-9.2",
            kind="deterministic",
            status="pass" if out_only else "fail",
            evidence="mention sits in outro" if out_only else "mention found outside outro",
        )
    )
    # A-9.3: Mynaani sentence ≤ 12 spoken words
    if mentions_in_outro:
        sentence = _sentence_containing(outro, "mynaani")
        sw = word_count(sentence)
        out.append(
            Check(
                id="A-9.3",
                clause="C-9.3",
                kind="deterministic",
                status="pass" if sw <= MYNAANI_MAX_WORDS else "fail",
                evidence=f"mynaani sentence has {sw} words (limit {MYNAANI_MAX_WORDS})",
            )
        )
    # A-9.5: never "patented"; "patent-pending" at most once
    patented_hits = re.findall(r"\bpatented\b", full, flags=re.IGNORECASE)
    pending_hits = re.findall(r"\bpatent[- ]pending\b", full, flags=re.IGNORECASE)
    out.append(
        Check(
            id="A-9.5",
            clause="C-9.3",
            kind="deterministic",
            status="pass" if not patented_hits and len(pending_hits) <= 1 else "fail",
            evidence=f"'patented' hits = {len(patented_hits)}, 'patent-pending' hits = {len(pending_hits)}",
        )
    )
    # A-9.6: 'subscribe' at most once, outro only
    subs_full = re.findall(r"\bsubscribe\b", full, flags=re.IGNORECASE)
    subs_outro = re.findall(r"\bsubscribe\b", outro, flags=re.IGNORECASE)
    ok = len(subs_full) <= 1 and len(subs_full) == len(subs_outro)
    out.append(
        Check(
            id="A-9.6",
            clause="C-9.4",
            kind="deterministic",
            status="pass" if ok else "fail",
            evidence=f"subscribe full = {len(subs_full)}, in outro = {len(subs_outro)}",
        )
    )
    return out


def _sentence_containing(text: str, needle: str) -> str:
    parts = re.split(r"(?<=[.!?])\s+", text)
    for p in parts:
        if needle.lower() in p.lower():
            return p
    return text


# --------------------------------------------------------------------------- #
# Entry point                                                                 #
# --------------------------------------------------------------------------- #


def audit_script(path: Path) -> AuditReport:
    """Run all deterministic checks against the given script file."""
    fm, _body = parse_script(path)
    script_id = str(fm.get("id") or path.parent.name)

    checks: list[Check] = [
        check_frontmatter_present(fm),
        check_beats_present(fm),
        check_walkthrough_steps(fm),
        check_wpm(fm),
        check_window_wpm(fm),
        check_beat_order(fm),
        check_named_win(fm),
        check_recovery_substance(fm),
    ]
    checks.extend(check_forbidden_patterns(fm))
    checks.extend(check_mynaani_rules(fm))

    return AuditReport(
        script_id=script_id,
        contract_version=CONTRACT_VERSION,
        audited_at=datetime.now(tz=UTC).isoformat(timespec="seconds"),
        checks=checks,
    )


def write_audit_report(report: AuditReport, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "audit.json"
    target.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    return target
