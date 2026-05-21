"""Sanity tests for the forbidden-patterns YAML."""

from __future__ import annotations

import yaml

from pipeline.audit import FORBIDDEN_PATTERNS_PATH


def test_forbidden_patterns_yaml_parses():
    data = yaml.safe_load(FORBIDDEN_PATTERNS_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert data, "forbidden_patterns.yaml must not be empty"


def test_every_clause_has_at_least_one_pattern():
    data = yaml.safe_load(FORBIDDEN_PATTERNS_PATH.read_text(encoding="utf-8"))
    for clause, patterns in data.items():
        assert isinstance(patterns, list), f"{clause} must map to a list"
        assert all(isinstance(p, str) and p for p in patterns), f"{clause} has empty entries"
        assert len(patterns) >= 1


def test_clauses_use_canonical_ids():
    data = yaml.safe_load(FORBIDDEN_PATTERNS_PATH.read_text(encoding="utf-8"))
    for clause in data:
        assert clause.startswith("C-4."), f"unexpected clause id: {clause}"
