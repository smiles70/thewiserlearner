"""YouTube Data API v3 publisher.

Uploads an MP4 to the channel, sets title/description/tags from a YAML metadata
file, attaches a thumbnail, and (optionally) adds the video to a playlist.

Authentication is OAuth 2.0 with offline access. The first run opens a browser
to authorise; subsequent runs use the cached refresh token. Credentials never
land in this repo.

    Required env vars (or `oauth_secrets_path` argument):
        YOUTUBE_CLIENT_SECRETS  path to client_secret.json from Google Cloud Console
        YOUTUBE_TOKEN_CACHE     path to where the refresh token is cached

Metadata schema (``meta.yaml`` next to the script):

    title: "..."
    description: |
        ...
    tags: [...]
    category_id: "27"      # 27 = Education
    privacy_status: "private" | "unlisted" | "public"
    playlist_id: "PL..."    # optional
    made_for_kids: false    # MUST be false for this channel

CLI:
    python -m pipeline.cli publish episodes/E-001-foo/script.md
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

YOUTUBE_API_VERSION = "v3"
YOUTUBE_API_SERVICE = "youtube"
SCOPES = ("https://www.googleapis.com/auth/youtube.upload",)
DEFAULT_CATEGORY_ID = "27"  # Education
ALLOWED_PRIVACY = ("private", "unlisted", "public")


@dataclass
class PublishResult:
    video_id: str
    url: str
    privacy_status: str


# --------------------------------------------------------------------------- #
# Pure helpers                                                                #
# --------------------------------------------------------------------------- #


def load_metadata(meta_path: Path) -> dict[str, Any]:
    data = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{meta_path}: metadata must be a YAML mapping")
    return validate_metadata(data)


def validate_metadata(data: dict[str, Any]) -> dict[str, Any]:
    """Validate metadata; raise on contract or schema violations."""
    title = data.get("title")
    if not title or not isinstance(title, str):
        raise ValueError("meta.title is required (non-empty string)")
    if len(title) > 100:
        raise ValueError("meta.title must be <= 100 characters (YouTube limit)")
    desc = data.get("description") or ""
    if not isinstance(desc, str):
        raise ValueError("meta.description must be a string")
    if len(desc) > 5000:
        raise ValueError("meta.description must be <= 5000 characters (YouTube limit)")
    tags = data.get("tags") or []
    if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
        raise ValueError("meta.tags must be a list of strings")
    privacy = data.get("privacy_status", "private")
    if privacy not in ALLOWED_PRIVACY:
        raise ValueError(f"meta.privacy_status must be one of {ALLOWED_PRIVACY}")
    if data.get("made_for_kids") is True:
        raise ValueError("meta.made_for_kids must be false; channel is not directed at children")
    out = dict(data)
    out.setdefault("category_id", DEFAULT_CATEGORY_ID)
    out.setdefault("privacy_status", "private")
    out.setdefault("made_for_kids", False)
    out.setdefault("tags", [])
    out.setdefault("description", "")
    return out


def build_video_resource(meta: dict[str, Any]) -> dict[str, Any]:
    """Build the YouTube videos.insert request body. Pure: easy to unit-test."""
    return {
        "snippet": {
            "title": meta["title"],
            "description": meta["description"],
            "tags": meta["tags"],
            "categoryId": meta["category_id"],
            "defaultLanguage": meta.get("default_language", "en"),
            "defaultAudioLanguage": meta.get("default_audio_language", "en"),
        },
        "status": {
            "privacyStatus": meta["privacy_status"],
            "selfDeclaredMadeForKids": meta["made_for_kids"],
            "embeddable": meta.get("embeddable", True),
        },
    }


# --------------------------------------------------------------------------- #
# OAuth + API plumbing (network)                                              #
# --------------------------------------------------------------------------- #


def _build_service(  # pragma: no cover - network/oauth
    client_secrets_path: Path, token_cache_path: Path
):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds: Credentials | None = None
    if token_cache_path.is_file():
        creds = Credentials.from_authorized_user_file(str(token_cache_path), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets_path), SCOPES)
            creds = flow.run_local_server(port=0)
        token_cache_path.write_text(creds.to_json(), encoding="utf-8")
    return build(YOUTUBE_API_SERVICE, YOUTUBE_API_VERSION, credentials=creds)


def publish(  # pragma: no cover - network
    video_path: Path,
    meta_path: Path,
    *,
    thumbnail_path: Path | None = None,
    client_secrets_path: Path | None = None,
    token_cache_path: Path | None = None,
) -> PublishResult:
    """Upload ``video_path`` with metadata from ``meta_path``."""
    from googleapiclient.http import MediaFileUpload

    if not video_path.is_file():
        raise FileNotFoundError(video_path)
    meta = load_metadata(meta_path)

    cs = client_secrets_path or Path(os.environ.get("YOUTUBE_CLIENT_SECRETS", ""))
    tc = token_cache_path or Path(
        os.environ.get("YOUTUBE_TOKEN_CACHE", str(Path.home() / ".wiser-yt-token.json"))
    )
    if not cs or not cs.is_file():
        raise RuntimeError(
            "YouTube client secrets file not found; set YOUTUBE_CLIENT_SECRETS or pass "
            "client_secrets_path."
        )

    service = _build_service(cs, tc)
    body = build_video_resource(meta)
    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True, mimetype="video/mp4")
    request = service.videos().insert(part=",".join(body.keys()), body=body, media_body=media)
    response = None
    while response is None:
        _, response = request.next_chunk()
    video_id = response["id"]

    if thumbnail_path and thumbnail_path.is_file():
        service.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(str(thumbnail_path), mimetype="image/png"),
        ).execute()

    if meta.get("playlist_id"):
        service.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": meta["playlist_id"],
                    "resourceId": {"kind": "youtube#video", "videoId": video_id},
                }
            },
        ).execute()

    return PublishResult(
        video_id=video_id,
        url=f"https://www.youtube.com/watch?v={video_id}",
        privacy_status=meta["privacy_status"],
    )
