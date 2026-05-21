"""Tests for `pipeline.youtube` (pure helpers; no network)."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from pipeline import youtube as yt

# --------------------------------------------------------------------------- #
# validate_metadata                                                           #
# --------------------------------------------------------------------------- #


def _good():
    return {"title": "Hello", "description": "World.", "tags": ["a", "b"]}


def test_validate_metadata_fills_defaults():
    out = yt.validate_metadata(_good())
    assert out["category_id"] == yt.DEFAULT_CATEGORY_ID
    assert out["privacy_status"] == "private"
    assert out["made_for_kids"] is False


def test_validate_metadata_rejects_missing_title():
    with pytest.raises(ValueError):
        yt.validate_metadata({"description": "x"})


def test_validate_metadata_rejects_long_title():
    with pytest.raises(ValueError):
        yt.validate_metadata({"title": "x" * 101})


def test_validate_metadata_rejects_long_description():
    with pytest.raises(ValueError):
        yt.validate_metadata({"title": "ok", "description": "x" * 5001})


def test_validate_metadata_rejects_invalid_privacy():
    with pytest.raises(ValueError):
        yt.validate_metadata({"title": "ok", "privacy_status": "huh"})


def test_validate_metadata_rejects_made_for_kids_true():
    with pytest.raises(ValueError):
        yt.validate_metadata({"title": "ok", "made_for_kids": True})


def test_validate_metadata_rejects_non_string_tags():
    with pytest.raises(ValueError):
        yt.validate_metadata({"title": "ok", "tags": [1, 2]})


# --------------------------------------------------------------------------- #
# build_video_resource                                                        #
# --------------------------------------------------------------------------- #


def test_build_video_resource_includes_required_fields():
    meta = yt.validate_metadata(_good())
    body = yt.build_video_resource(meta)
    assert body["snippet"]["title"] == "Hello"
    assert body["snippet"]["categoryId"] == yt.DEFAULT_CATEGORY_ID
    assert body["status"]["privacyStatus"] == "private"
    assert body["status"]["selfDeclaredMadeForKids"] is False


def test_build_video_resource_defaults_language_to_en():
    meta = yt.validate_metadata(_good())
    body = yt.build_video_resource(meta)
    assert body["snippet"]["defaultLanguage"] == "en"
    assert body["snippet"]["defaultAudioLanguage"] == "en"


# --------------------------------------------------------------------------- #
# load_metadata (file IO + YAML)                                              #
# --------------------------------------------------------------------------- #


def test_load_metadata_reads_yaml(tmp_path: Path):
    p = tmp_path / "meta.yaml"
    p.write_text(
        textwrap.dedent("""
            title: "Hello"
            description: "World."
            tags: ["a", "b"]
            privacy_status: unlisted
        """).strip(),
        encoding="utf-8",
    )
    out = yt.load_metadata(p)
    assert out["title"] == "Hello"
    assert out["privacy_status"] == "unlisted"
    assert out["made_for_kids"] is False


def test_load_metadata_rejects_non_mapping(tmp_path: Path):
    p = tmp_path / "meta.yaml"
    p.write_text("- 1\n- 2\n", encoding="utf-8")
    with pytest.raises(ValueError):
        yt.load_metadata(p)
