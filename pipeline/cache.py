"""Content-addressed cache for paid generations (images, audio, text).

Keys are sha256 of a stable serialisation of (provider, model, prompt, params).
Values are stored on disk under `.cache/<namespace>/<hash>.<ext>` with a
sidecar `.json` containing the request metadata. Re-running the same prompt
returns the cached path instead of re-charging the provider.

This is intentionally a tiny module; no LRU eviction, no TTL. The cache grows
monotonically and is git-ignored.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def cache_key(*, provider: str, model: str, prompt: str, params: dict[str, Any]) -> str:
    """Deterministic sha256 over a normalised JSON serialisation."""
    payload = {
        "provider": provider,
        "model": model,
        "prompt": prompt,
        "params": params,
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


@dataclass
class CacheHit:
    path: Path
    metadata: dict[str, Any]


class ContentCache:
    def __init__(self, root: Path, namespace: str) -> None:
        self.root = Path(root) / namespace
        self.root.mkdir(parents=True, exist_ok=True)

    def _paths(self, key: str, ext: str) -> tuple[Path, Path]:
        return self.root / f"{key}.{ext}", self.root / f"{key}.json"

    def get(self, key: str, ext: str) -> CacheHit | None:
        data_path, meta_path = self._paths(key, ext)
        if not data_path.is_file() or not meta_path.is_file():
            return None
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        return CacheHit(path=data_path, metadata=meta)

    def put(
        self,
        *,
        key: str,
        ext: str,
        source_path: Path,
        metadata: dict[str, Any],
    ) -> Path:
        data_path, meta_path = self._paths(key, ext)
        if Path(source_path).resolve() != data_path.resolve():
            shutil.copyfile(source_path, data_path)
        meta_path.write_text(
            json.dumps(metadata, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return data_path

    def put_bytes(
        self,
        *,
        key: str,
        ext: str,
        data: bytes,
        metadata: dict[str, Any],
    ) -> Path:
        data_path, meta_path = self._paths(key, ext)
        data_path.write_bytes(data)
        meta_path.write_text(
            json.dumps(metadata, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return data_path
