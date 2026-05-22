"""Spend guard for paid external APIs (Anthropic, fal.ai, etc.).

Tracks per-episode and per-day spend in a JSON ledger and blocks calls that
would exceed the configured caps. Pure Python + filesystem; no network.

Usage::

    guard = CostGuard.load(ledger_path=Path(".cache/spend.json"))
    guard.check_and_charge(provider="fal", amount_usd=0.05, episode_id="E-001")

Caps come from env vars (override at runtime, never hard-coded):
    EPISODE_USD_CAP   default 5.00
    DAILY_USD_CAP     default 25.00

If a charge would push past either cap, raises BudgetExceeded; the ledger is
not updated.
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_EPISODE_CAP_USD = 5.00
DEFAULT_DAILY_CAP_USD = 25.00


class BudgetExceeded(RuntimeError):
    """Raised when a charge would push past the configured cap."""


@dataclass
class Charge:
    timestamp: str  # ISO 8601 UTC
    provider: str
    amount_usd: float
    episode_id: str
    note: str = ""


@dataclass
class CostGuard:
    ledger_path: Path
    charges: list[Charge] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @classmethod
    def load(cls, ledger_path: Path) -> CostGuard:
        ledger_path = Path(ledger_path)
        if not ledger_path.exists():
            return cls(ledger_path=ledger_path, charges=[])
        raw = json.loads(ledger_path.read_text(encoding="utf-8"))
        charges = [Charge(**row) for row in raw.get("charges", [])]
        return cls(ledger_path=ledger_path, charges=charges)

    # ---- caps ----

    @staticmethod
    def episode_cap_usd() -> float:
        return float(os.environ.get("EPISODE_USD_CAP", DEFAULT_EPISODE_CAP_USD))

    @staticmethod
    def daily_cap_usd() -> float:
        return float(os.environ.get("DAILY_USD_CAP", DEFAULT_DAILY_CAP_USD))

    # ---- queries ----

    def episode_spend(self, episode_id: str) -> float:
        return round(sum(c.amount_usd for c in self.charges if c.episode_id == episode_id), 6)

    def daily_spend(self, day: str | None = None) -> float:
        """Spend on the given UTC day (YYYY-MM-DD); default = today UTC."""
        if day is None:
            day = datetime.now(UTC).strftime("%Y-%m-%d")
        return round(
            sum(c.amount_usd for c in self.charges if c.timestamp.startswith(day)),
            6,
        )

    # ---- mutation ----

    def check_and_charge(
        self,
        *,
        provider: str,
        amount_usd: float,
        episode_id: str,
        note: str = "",
    ) -> Charge:
        if amount_usd < 0:
            raise ValueError("amount_usd must be non-negative")
        with self._lock:
            ep_after = self.episode_spend(episode_id) + amount_usd
            day_after = self.daily_spend() + amount_usd
            if ep_after > self.episode_cap_usd():
                raise BudgetExceeded(
                    f"episode {episode_id} would spend ${ep_after:.4f} > cap ${self.episode_cap_usd():.2f}"
                )
            if day_after > self.daily_cap_usd():
                raise BudgetExceeded(
                    f"today would spend ${day_after:.4f} > cap ${self.daily_cap_usd():.2f}"
                )
            charge = Charge(
                timestamp=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                provider=provider,
                amount_usd=round(amount_usd, 6),
                episode_id=episode_id,
                note=note,
            )
            self.charges.append(charge)
            self._flush()
            return charge

    def _flush(self) -> None:
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"charges": [c.__dict__ for c in self.charges]}
        self.ledger_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
