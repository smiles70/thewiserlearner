"""Visual provider registry.

Selects between LocalProvider (offline gradients) and FalProvider (real AI
imagery via fal.ai). Selection is driven by the ``VISUAL_PROVIDER`` env var:

    VISUAL_PROVIDER=local  -> always LocalProvider (offline)
    VISUAL_PROVIDER=fal    -> FalProvider when FAL_KEY is set, else
                              raises so the caller knows to fix env

If unset, defaults to ``local`` (no surprise paid calls).
"""

from __future__ import annotations

import os

from pipeline.visuals import LocalProvider, VisualProvider


def get_provider(name: str | None = None) -> VisualProvider:
    name = (name or os.environ.get("VISUAL_PROVIDER") or "local").lower()
    if name == "local":
        return LocalProvider()
    if name == "fal":
        from pipeline.providers.fal import FalProvider

        return FalProvider.from_env()
    raise ValueError(f"unknown VISUAL_PROVIDER {name!r}; expected one of: local, fal")


__all__ = ["get_provider"]
