"""YouTube Data API publisher.

Stubbed in v0.1.0. The production implementation will use the YouTube Data
API v3 to upload an MP4, set title/description/tags from the SEO manifest,
upload the thumbnail, and add the video to the playlist. OAuth credentials
live in repo secrets and never on disk.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class PublishResult:
    video_id: str
    url: str


def publish(  # pragma: no cover - stub
    video_path: Path, seo_manifest_path: Path, thumbnail_path: Path
) -> PublishResult:
    raise NotImplementedError(
        "pipeline.youtube.publish is stubbed in v0.1.0. Implementation arrives "
        "in pipeline-part-10 (publishing)."
    )
