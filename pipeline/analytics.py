"""YouTube analytics ingest.

Fetches per-video metrics (views, watch time, average view duration, comment
count, like count) and writes them to `analytics/<video_id>.json`. Used as
input to the analyst agent.

Mock mode
---------
If env `ANALYTICS_MOCK=1` is set, returns a deterministic canned record
without touching the network. This lets `run_episode` exercise the full
post-publish path in tests and CI without YouTube credentials.

Live mode requires `YOUTUBE_DATA_API_KEY` (or OAuth credentials if you want
private-channel metrics; this minimal implementation uses an API key against
the public Data API endpoint).
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, Field

YT_API_BASE = "https://www.googleapis.com/youtube/v3"


class VideoMetrics(BaseModel):
    video_id: str
    fetched_at: str
    title: str
    duration_iso8601: str
    view_count: int = Field(ge=0)
    like_count: int = Field(ge=0)
    comment_count: int = Field(ge=0)
    # Note: watch_time and average_view_duration require YouTube Analytics
    # API (OAuth), not the public Data API. Left optional here.
    watch_time_seconds: float | None = None
    average_view_duration_seconds: float | None = None


def fetch_video_metrics(
    *,
    video_id: str,
    client: httpx.Client | None = None,
) -> VideoMetrics:
    """Fetch the public metrics for a video. Mock-safe."""
    if os.environ.get("ANALYTICS_MOCK") == "1":
        return _mock_metrics(video_id)

    api_key = os.environ.get("YOUTUBE_DATA_API_KEY")
    if not api_key:
        raise RuntimeError(
            "YOUTUBE_DATA_API_KEY not set; set ANALYTICS_MOCK=1 for mock mode"
        )
    own = client is None
    client = client or httpx.Client(timeout=20.0)
    try:
        r = client.get(
            f"{YT_API_BASE}/videos",
            params={"part": "snippet,statistics,contentDetails", "id": video_id, "key": api_key},
        )
        if r.status_code >= 400:
            raise RuntimeError(f"YouTube API error {r.status_code}: {r.text}")
        body = r.json()
    finally:
        if own:
            client.close()

    items = body.get("items") or []
    if not items:
        raise RuntimeError(f"video {video_id!r} not found")
    item = items[0]
    snip = item.get("snippet", {})
    stat = item.get("statistics", {})
    cd = item.get("contentDetails", {})
    return VideoMetrics(
        video_id=video_id,
        fetched_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        title=snip.get("title", ""),
        duration_iso8601=cd.get("duration", "PT0S"),
        view_count=int(stat.get("viewCount", 0)),
        like_count=int(stat.get("likeCount", 0)),
        comment_count=int(stat.get("commentCount", 0)),
    )


def _mock_metrics(video_id: str) -> VideoMetrics:
    return VideoMetrics(
        video_id=video_id,
        fetched_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        title="MOCK: AI is everywhere",
        duration_iso8601="PT5M0S",
        view_count=123,
        like_count=7,
        comment_count=2,
        watch_time_seconds=410.0,
        average_view_duration_seconds=205.0,
    )


def write_metrics(metrics: VideoMetrics, out_dir: Path) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{metrics.video_id}.json"
    out_path.write_text(
        json.dumps(metrics.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    return out_path


def load_recent_metrics(out_dir: Path, *, limit: int = 10) -> list[dict[str, Any]]:
    """Load up to `limit` most-recent metrics from `analytics/`."""
    out_dir = Path(out_dir)
    if not out_dir.is_dir():
        return []
    files = sorted(out_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    rows: list[dict[str, Any]] = []
    for path in files[:limit]:
        try:
            rows.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return rows
