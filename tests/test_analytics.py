"""Tests for pipeline.analytics (mock-mode + httpx MockTransport for live)."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from pipeline.analytics import (
    VideoMetrics,
    fetch_video_metrics,
    load_recent_metrics,
    write_metrics,
)


def test_fetch_metrics_mock_mode(monkeypatch):
    monkeypatch.setenv("ANALYTICS_MOCK", "1")
    m = fetch_video_metrics(video_id="abc123")
    assert isinstance(m, VideoMetrics)
    assert m.video_id == "abc123"
    assert m.view_count >= 0


def test_fetch_metrics_missing_key_raises(monkeypatch):
    monkeypatch.delenv("ANALYTICS_MOCK", raising=False)
    monkeypatch.delenv("YOUTUBE_DATA_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="YOUTUBE_DATA_API_KEY"):
        fetch_video_metrics(video_id="abc123")


def test_fetch_metrics_live_via_mock_transport(monkeypatch):
    monkeypatch.delenv("ANALYTICS_MOCK", raising=False)
    monkeypatch.setenv("YOUTUBE_DATA_API_KEY", "fake")

    def handler(request: httpx.Request) -> httpx.Response:
        assert "videos" in str(request.url)
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "snippet": {"title": "Title"},
                        "statistics": {
                            "viewCount": "42",
                            "likeCount": "5",
                            "commentCount": "1",
                        },
                        "contentDetails": {"duration": "PT4M30S"},
                    }
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://t")
    m = fetch_video_metrics(video_id="abc", client=client)
    assert m.title == "Title"
    assert m.view_count == 42


def test_fetch_metrics_no_items_raises(monkeypatch):
    monkeypatch.delenv("ANALYTICS_MOCK", raising=False)
    monkeypatch.setenv("YOUTUBE_DATA_API_KEY", "fake")
    client = httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"items": []})),
        base_url="http://t",
    )
    with pytest.raises(RuntimeError, match="not found"):
        fetch_video_metrics(video_id="missing", client=client)


def test_write_and_load_recent_metrics(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("ANALYTICS_MOCK", "1")
    m1 = fetch_video_metrics(video_id="vid1")
    m2 = fetch_video_metrics(video_id="vid2")
    write_metrics(m1, tmp_path)
    write_metrics(m2, tmp_path)
    rows = load_recent_metrics(tmp_path, limit=10)
    assert {row["video_id"] for row in rows} == {"vid1", "vid2"}


def test_load_recent_metrics_missing_dir_returns_empty(tmp_path: Path):
    rows = load_recent_metrics(tmp_path / "nope", limit=5)
    assert rows == []


def test_load_recent_metrics_skips_garbage(tmp_path: Path):
    (tmp_path / "broken.json").write_text("not json", encoding="utf-8")
    (tmp_path / "good.json").write_text(json.dumps({"video_id": "x"}), encoding="utf-8")
    rows = load_recent_metrics(tmp_path, limit=10)
    assert rows == [{"video_id": "x"}]
