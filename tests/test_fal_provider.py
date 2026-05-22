"""Tests for FalProvider using httpx.MockTransport (no network)."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from pipeline.cache import ContentCache
from pipeline.cost_guard import BudgetExceeded, CostGuard
from pipeline.providers import get_provider
from pipeline.providers.fal import FalError, FalProvider
from pipeline.storyboard import BeatComposition, VisualTheme
from pipeline.visuals import LocalProvider

# A small fake 1x1 PNG (smallest valid PNG header + IEND).
FAKE_PNG = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
    b"\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01" b"\x5b\xb5\xa9\xc2"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _beat() -> BeatComposition:
    return BeatComposition.model_validate(
        {
            "beat": "hook",
            "image_prompt": "A warm morning kitchen with a kettle on the stove",
            "title": "Welcome.",
            "title_font_px": 96,
            "body_font_px": 56,
            "contrast_ratio": 8.0,
            "dwell_seconds": 5.0,
        }
    )


def _theme() -> VisualTheme:
    return VisualTheme.model_validate(
        {"palette": "warm-neutral-morning-light", "mood": "calm-morning-light"}
    )


def _mock_transport(responses: list[httpx.Response]) -> httpx.MockTransport:
    """Return a MockTransport that yields the given responses in order."""
    iterator = iter(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        try:
            return next(iterator)
        except StopIteration as exc:
            raise AssertionError(f"unexpected extra request to {request.url}") from exc

    return httpx.MockTransport(handler)


def _happy_path_responses() -> list[httpx.Response]:
    return [
        httpx.Response(200, json={"request_id": "req-123"}),
        httpx.Response(200, json={"status": "COMPLETED"}),
        httpx.Response(200, json={"images": [{"url": "https://cdn.fal.ai/img.png"}]}),
        httpx.Response(200, content=FAKE_PNG),
    ]


def _make_client(transport: httpx.MockTransport) -> httpx.Client:
    return httpx.Client(transport=transport, base_url="http://test", timeout=5.0)


# ---------- happy path ----------


def test_fal_happy_path_writes_png(tmp_path: Path):
    client = _make_client(_mock_transport(_happy_path_responses()))
    prov = FalProvider(api_key="test", client=client)
    out = prov.generate(_beat(), _theme(), tmp_path / "hook.png")
    assert out.read_bytes() == FAKE_PNG


def test_fal_polls_until_completed(tmp_path: Path):
    responses = [
        httpx.Response(200, json={"request_id": "r"}),
        httpx.Response(200, json={"status": "IN_PROGRESS"}),
        httpx.Response(200, json={"status": "IN_QUEUE"}),
        httpx.Response(200, json={"status": "COMPLETED"}),
        httpx.Response(200, json={"images": [{"url": "https://cdn.fal.ai/x.png"}]}),
        httpx.Response(200, content=FAKE_PNG),
    ]
    client = _make_client(_mock_transport(responses))
    prov = FalProvider(api_key="test", client=client, poll_interval_s=0.0)
    out = prov.generate(_beat(), _theme(), tmp_path / "x.png")
    assert out.read_bytes() == FAKE_PNG


# ---------- error paths ----------


def test_fal_submit_failure_raises(tmp_path: Path):
    responses = [httpx.Response(401, text="bad key")]
    client = _make_client(_mock_transport(responses))
    prov = FalProvider(api_key="bad", client=client)
    with pytest.raises(FalError, match="submit failed"):
        prov.generate(_beat(), _theme(), tmp_path / "x.png")


def test_fal_job_failed_status_raises(tmp_path: Path):
    responses = [
        httpx.Response(200, json={"request_id": "r"}),
        httpx.Response(200, json={"status": "FAILED", "error": "nsfw"}),
    ]
    client = _make_client(_mock_transport(responses))
    prov = FalProvider(api_key="test", client=client, poll_interval_s=0.0)
    with pytest.raises(FalError, match="FAILED"):
        prov.generate(_beat(), _theme(), tmp_path / "x.png")


def test_fal_no_images_raises(tmp_path: Path):
    responses = [
        httpx.Response(200, json={"request_id": "r"}),
        httpx.Response(200, json={"status": "COMPLETED"}),
        httpx.Response(200, json={"images": []}),
    ]
    client = _make_client(_mock_transport(responses))
    prov = FalProvider(api_key="test", client=client, poll_interval_s=0.0)
    with pytest.raises(FalError, match="no images"):
        prov.generate(_beat(), _theme(), tmp_path / "x.png")


def test_fal_missing_key_from_env(monkeypatch):
    monkeypatch.delenv("FAL_KEY", raising=False)
    with pytest.raises(FalError, match="FAL_KEY"):
        FalProvider.from_env()


# ---------- cost guard integration ----------


def test_fal_records_charge_on_cost_guard(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("EPISODE_USD_CAP", "10")
    monkeypatch.setenv("DAILY_USD_CAP", "10")
    guard = CostGuard.load(tmp_path / "spend.json")
    client = _make_client(_mock_transport(_happy_path_responses()))
    prov = FalProvider(
        api_key="test", client=client, cost_guard=guard, episode_id="E-099"
    )
    prov.generate(_beat(), _theme(), tmp_path / "out.png")
    assert guard.episode_spend("E-099") == pytest.approx(0.025)


def test_fal_blocked_by_cost_guard(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("EPISODE_USD_CAP", "0.01")  # too small
    monkeypatch.setenv("DAILY_USD_CAP", "1.0")
    guard = CostGuard.load(tmp_path / "spend.json")
    # No HTTP calls expected because guard fires before submit.
    client = _make_client(_mock_transport([]))
    prov = FalProvider(api_key="test", client=client, cost_guard=guard, episode_id="E-099")
    with pytest.raises(BudgetExceeded):
        prov.generate(_beat(), _theme(), tmp_path / "out.png")


# ---------- cache integration ----------


def test_fal_cache_miss_then_hit(tmp_path: Path):
    cache = ContentCache(root=tmp_path / "cache", namespace="visuals")

    # First call: full network path.
    client1 = _make_client(_mock_transport(_happy_path_responses()))
    prov1 = FalProvider(api_key="test", client=client1, cache=cache)
    out1 = prov1.generate(_beat(), _theme(), tmp_path / "first.png")
    assert out1.read_bytes() == FAKE_PNG

    # Second call with empty mock transport: cache must serve without
    # any network call.
    client2 = _make_client(_mock_transport([]))
    prov2 = FalProvider(api_key="test", client=client2, cache=cache)
    out2 = prov2.generate(_beat(), _theme(), tmp_path / "second.png")
    assert out2.read_bytes() == FAKE_PNG


# ---------- registry ----------


def test_registry_default_returns_local(monkeypatch):
    monkeypatch.delenv("VISUAL_PROVIDER", raising=False)
    p = get_provider()
    assert isinstance(p, LocalProvider)


def test_registry_local_explicit(monkeypatch):
    monkeypatch.setenv("VISUAL_PROVIDER", "local")
    assert isinstance(get_provider(), LocalProvider)


def test_registry_fal_without_key_raises(monkeypatch):
    monkeypatch.setenv("VISUAL_PROVIDER", "fal")
    monkeypatch.delenv("FAL_KEY", raising=False)
    with pytest.raises(FalError, match="FAL_KEY"):
        get_provider()


def test_registry_unknown_name_raises():
    with pytest.raises(ValueError, match="unknown VISUAL_PROVIDER"):
        get_provider("nope")
