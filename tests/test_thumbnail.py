"""Tests for pipeline.thumbnail.

We don't render a real video; we synthesise a tiny test mp4 with ffmpeg
(if available) and then extract a frame from it. Skipped if ffmpeg is not
installed on the test runner.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from pipeline.thumbnail import extract_thumbnail

ffmpeg_missing = pytest.mark.skipif(
    shutil.which("ffmpeg") is None,
    reason="ffmpeg required for thumbnail tests",
)


def _make_test_video(out_path: Path, duration_s: float = 10.0) -> Path:
    """Create a tiny solid-color test video."""
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c=blue:s=320x180:d={duration_s}",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        str(out_path),
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return out_path


@ffmpeg_missing
def test_extract_thumbnail_writes_png(tmp_path: Path):
    video = _make_test_video(tmp_path / "in.mp4")
    out = extract_thumbnail(video, out_path=tmp_path / "thumb.png", timestamp_seconds=2.0)
    assert out.is_file()
    assert out.stat().st_size > 0
    # PNG magic number check
    assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


@ffmpeg_missing
def test_extract_thumbnail_scales_to_full_hd(tmp_path: Path):
    video = _make_test_video(tmp_path / "in.mp4")
    out = extract_thumbnail(video, out_path=tmp_path / "thumb.png")
    from PIL import Image

    with Image.open(out) as img:
        assert img.size == (1920, 1080)


def test_extract_thumbnail_missing_video_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        extract_thumbnail(
            tmp_path / "nope.mp4",
            out_path=tmp_path / "thumb.png",
        )


def test_extract_thumbnail_negative_timestamp_raises(tmp_path: Path):
    video = tmp_path / "in.mp4"
    video.write_bytes(b"")  # Doesn't matter; check fires before ffmpeg call.
    # FileNotFoundError takes precedence; create real file but require ffmpeg.
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg required")
    video = _make_test_video(video)
    with pytest.raises(ValueError):
        extract_thumbnail(video, out_path=tmp_path / "t.png", timestamp_seconds=-1.0)
