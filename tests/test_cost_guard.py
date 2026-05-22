"""Tests for CostGuard."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipeline.cost_guard import BudgetExceeded, CostGuard


def test_empty_ledger(tmp_path: Path):
    g = CostGuard.load(tmp_path / "spend.json")
    assert g.charges == []
    assert g.episode_spend("E-001") == 0.0
    assert g.daily_spend() == 0.0


def test_charge_writes_to_ledger(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("EPISODE_USD_CAP", "5.00")
    monkeypatch.setenv("DAILY_USD_CAP", "10.00")
    p = tmp_path / "spend.json"
    g = CostGuard.load(p)
    g.check_and_charge(provider="fal", amount_usd=0.05, episode_id="E-001")
    g.check_and_charge(provider="fal", amount_usd=0.05, episode_id="E-001")
    raw = json.loads(p.read_text(encoding="utf-8"))
    assert len(raw["charges"]) == 2
    assert g.episode_spend("E-001") == pytest.approx(0.10)


def test_episode_cap_blocks_charge(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("EPISODE_USD_CAP", "0.10")
    monkeypatch.setenv("DAILY_USD_CAP", "100.00")
    g = CostGuard.load(tmp_path / "spend.json")
    g.check_and_charge(provider="fal", amount_usd=0.08, episode_id="E-001")
    with pytest.raises(BudgetExceeded, match="episode E-001"):
        g.check_and_charge(provider="fal", amount_usd=0.05, episode_id="E-001")
    # the second charge must NOT be persisted
    assert g.episode_spend("E-001") == pytest.approx(0.08)


def test_daily_cap_blocks_charge(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("EPISODE_USD_CAP", "100.00")
    monkeypatch.setenv("DAILY_USD_CAP", "0.10")
    g = CostGuard.load(tmp_path / "spend.json")
    g.check_and_charge(provider="fal", amount_usd=0.08, episode_id="E-001")
    with pytest.raises(BudgetExceeded, match="today would spend"):
        g.check_and_charge(provider="fal", amount_usd=0.05, episode_id="E-002")


def test_negative_charge_rejected(tmp_path: Path):
    g = CostGuard.load(tmp_path / "spend.json")
    with pytest.raises(ValueError):
        g.check_and_charge(provider="fal", amount_usd=-1.0, episode_id="E-001")


def test_reload_round_trip(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("EPISODE_USD_CAP", "100")
    monkeypatch.setenv("DAILY_USD_CAP", "100")
    p = tmp_path / "spend.json"
    g = CostGuard.load(p)
    g.check_and_charge(provider="anthropic", amount_usd=0.20, episode_id="E-002")
    g2 = CostGuard.load(p)
    assert len(g2.charges) == 1
    assert g2.episode_spend("E-002") == pytest.approx(0.20)


def test_per_episode_isolation(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("EPISODE_USD_CAP", "0.30")
    monkeypatch.setenv("DAILY_USD_CAP", "100")
    g = CostGuard.load(tmp_path / "spend.json")
    g.check_and_charge(provider="fal", amount_usd=0.25, episode_id="E-001")
    # another episode unaffected
    g.check_and_charge(provider="fal", amount_usd=0.25, episode_id="E-002")
    assert g.episode_spend("E-001") == pytest.approx(0.25)
    assert g.episode_spend("E-002") == pytest.approx(0.25)
