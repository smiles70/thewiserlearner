"""Thumbnail extraction from a finished episode mp4.

Pulls a single frame from a chosen timestamp (default: 5.0 s, well into the
hook beat) and writes it as a 1920x1080 PNG next to the script as
`thumbnail.png`. The compositor's burned title is included in the frame, so
the thumbnail inherits the same calm aesthetic as the video itself - no
separate design step required.

This module is deliberately ffmpeg-only (no Pillow filters, no overlays):
it captures whatever the video already shows. If you want richer thumbnails
later, swap this for a fal.ai generation step using `pipeline.providers.fal`.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def extract_thumbnail(
    video_path: Path,
    *,
    out_path: Path,
    timestamp_seconds: float = 5.0,
) -> Path:
    """Extract a single frame at `timestamp_seconds` from the video.

    Returns the written PNG path. Raises RuntimeError if ffmpeg is missing
    or the extraction produces a 0-byte file.
    """
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg must be on PATH to extract thumbnails")
    if not video_path.is_file():
        raise FileNotFoundError(f"video not found: {video_path}")
    if timestamp_seconds < 0:
        raise ValueError("timestamp_seconds must be non-negative")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{timestamp_seconds:.3f}",
        "-i",
        str(video_path),
        "-vframes",
        "1",
        "-vf",
        "scale=1920:1080",
        "-q:v",
        "2",
        str(out_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg thumbnail extraction failed:\n{result.stderr.strip()}"
        )
    if not out_path.is_file() or out_path.stat().st_size == 0:
        raise RuntimeError(f"ffmpeg produced no thumbnail at {out_path}")
    return out_path
