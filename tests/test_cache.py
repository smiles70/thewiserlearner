"""Tests for ContentCache."""

from __future__ import annotations

from pathlib import Path

from pipeline.cache import ContentCache, cache_key


def test_cache_key_deterministic_and_param_sensitive():
    a = cache_key(provider="fal", model="flux/dev", prompt="hello", params={"w": 1024})
    b = cache_key(provider="fal", model="flux/dev", prompt="hello", params={"w": 1024})
    c = cache_key(provider="fal", model="flux/dev", prompt="hello", params={"w": 768})
    d = cache_key(provider="fal", model="flux/dev", prompt="hello!", params={"w": 1024})
    assert a == b
    assert a != c
    assert a != d
    assert len(a) == 64


def test_cache_miss_then_hit_via_put_bytes(tmp_path: Path):
    cache = ContentCache(root=tmp_path, namespace="visuals")
    key = cache_key(provider="fal", model="flux/dev", prompt="orb", params={})
    assert cache.get(key, ext="png") is None
    cache.put_bytes(key=key, ext="png", data=b"\x89PNG\r\n", metadata={"prompt": "orb"})
    hit = cache.get(key, ext="png")
    assert hit is not None
    assert hit.path.read_bytes() == b"\x89PNG\r\n"
    assert hit.metadata == {"prompt": "orb"}


def test_cache_put_from_path(tmp_path: Path):
    cache = ContentCache(root=tmp_path / "c", namespace="visuals")
    src = tmp_path / "in.png"
    src.write_bytes(b"\x00\x01\x02")
    key = "abc" + "0" * 61
    cache.put(key=key, ext="png", source_path=src, metadata={"k": "v"})
    hit = cache.get(key, ext="png")
    assert hit is not None
    assert hit.path.read_bytes() == b"\x00\x01\x02"
    assert hit.metadata == {"k": "v"}


def test_cache_namespaces_are_isolated(tmp_path: Path):
    a = ContentCache(root=tmp_path, namespace="images")
    b = ContentCache(root=tmp_path, namespace="audio")
    a.put_bytes(key="k", ext="png", data=b"img", metadata={})
    assert a.get("k", "png") is not None
    assert b.get("k", "png") is None
