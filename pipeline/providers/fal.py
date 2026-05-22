"""fal.ai image-generation provider.

Implements the `VisualProvider` protocol from `pipeline.visuals` against
fal.ai's queue API. One generation per beat. Prompts come straight from
`BeatComposition.image_prompt`; the provider hardens them against contract
violations (faces, blue/yellow-only meaning, text-on-image) by appending a
fixed safety suffix.

Behaviour:

    1. Compute a content-cache key over (model, prompt, size, safety_suffix).
    2. If cached, copy the cached PNG to `out_path` and return.
    3. Else estimate cost, call CostGuard.check_and_charge (raises if over
       cap), submit the queue job, poll until done, download bytes, write
       to both the cache and `out_path`.

Network calls are isolated behind a single `httpx.Client` so tests can inject
a transport.

Defaults aim at cheap/calm output: model ``fal-ai/flux/dev``, 1920x1080,
guidance 3.0. Override via env: ``FAL_MODEL``, ``FAL_GUIDANCE``,
``FAL_NUM_INFERENCE_STEPS``.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from pipeline.cache import ContentCache, cache_key
from pipeline.cost_guard import CostGuard
from pipeline.storyboard import BeatComposition, VisualTheme

DEFAULT_MODEL = "fal-ai/flux/dev"
QUEUE_BASE = "https://queue.fal.run"
DEFAULT_WIDTH = 1920
DEFAULT_HEIGHT = 1080
DEFAULT_USD_PER_IMAGE = 0.025  # flux/dev published price; conservative estimate

SAFETY_SUFFIX = (
    " -- aesthetic: calm, geragogy-friendly, no faces, no text, "
    "no logos, no readable signage, soft natural light, "
    "warm neutral palette, painterly background. "
    "Composition leaves the centre clear for caption overlay."
)


class FalError(RuntimeError):
    """Raised on any unrecoverable fal.ai error."""


@dataclass
class FalProvider:
    api_key: str
    model: str = DEFAULT_MODEL
    width: int = DEFAULT_WIDTH
    height: int = DEFAULT_HEIGHT
    guidance_scale: float = 3.0
    num_inference_steps: int = 28
    usd_per_image: float = DEFAULT_USD_PER_IMAGE
    poll_interval_s: float = 1.5
    poll_timeout_s: float = 120.0
    episode_id: str = "unknown"
    cost_guard: CostGuard | None = None
    cache: ContentCache | None = None
    client: httpx.Client | None = None

    # ---- construction ----

    @classmethod
    def from_env(
        cls,
        *,
        episode_id: str = "unknown",
        cost_guard: CostGuard | None = None,
        cache: ContentCache | None = None,
        client: httpx.Client | None = None,
    ) -> FalProvider:
        api_key = os.environ.get("FAL_KEY")
        if not api_key:
            raise FalError("FAL_KEY env var not set; cannot create FalProvider")
        return cls(
            api_key=api_key,
            model=os.environ.get("FAL_MODEL", DEFAULT_MODEL),
            guidance_scale=float(os.environ.get("FAL_GUIDANCE", "3.0")),
            num_inference_steps=int(os.environ.get("FAL_NUM_INFERENCE_STEPS", "28")),
            episode_id=episode_id,
            cost_guard=cost_guard,
            cache=cache,
            client=client,
        )

    # ---- protocol ----

    def generate(
        self,
        beat: BeatComposition,
        theme: VisualTheme,
        out_path: Path,
    ) -> Path:
        prompt = self._build_prompt(beat, theme)
        params = {
            "image_size": {"width": self.width, "height": self.height},
            "guidance_scale": self.guidance_scale,
            "num_inference_steps": self.num_inference_steps,
        }
        key = cache_key(provider="fal", model=self.model, prompt=prompt, params=params)

        if self.cache is not None:
            hit = self.cache.get(key, ext="png")
            if hit is not None:
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_bytes(hit.path.read_bytes())
                return out_path

        if self.cost_guard is not None:
            self.cost_guard.check_and_charge(
                provider="fal",
                amount_usd=self.usd_per_image,
                episode_id=self.episode_id,
                note=f"beat={beat.beat} model={self.model}",
            )

        png_bytes = self._call_fal(prompt=prompt, params=params)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(png_bytes)

        if self.cache is not None:
            self.cache.put_bytes(
                key=key,
                ext="png",
                data=png_bytes,
                metadata={
                    "prompt": prompt,
                    "model": self.model,
                    "params": params,
                    "beat": beat.beat,
                },
            )
        return out_path

    # ---- helpers ----

    def _build_prompt(self, beat: BeatComposition, theme: VisualTheme) -> str:
        return f"{beat.image_prompt.strip()} -- palette: {theme.palette}.{SAFETY_SUFFIX}"

    def _client(self) -> httpx.Client:
        if self.client is not None:
            return self.client
        return httpx.Client(
            timeout=30.0,
            headers={
                "Authorization": f"Key {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

    def _call_fal(self, *, prompt: str, params: dict[str, Any]) -> bytes:
        client = self._client()
        # 1. Submit
        submit_url = f"{QUEUE_BASE}/{self.model}"
        payload: dict[str, Any] = {"prompt": prompt, **params}
        r = client.post(submit_url, json=payload)
        if r.status_code >= 400:
            raise FalError(f"fal submit failed: {r.status_code} {r.text}")
        request_id = r.json().get("request_id")
        if not request_id:
            raise FalError(f"fal submit returned no request_id: {r.text}")

        # 2. Poll
        status_url = f"{QUEUE_BASE}/{self.model}/requests/{request_id}/status"
        result_url = f"{QUEUE_BASE}/{self.model}/requests/{request_id}"
        deadline = time.monotonic() + self.poll_timeout_s
        while time.monotonic() < deadline:
            sr = client.get(status_url)
            if sr.status_code >= 400:
                raise FalError(f"fal status failed: {sr.status_code} {sr.text}")
            status = sr.json().get("status")
            if status == "COMPLETED":
                break
            if status in {"FAILED", "CANCELLED"}:
                raise FalError(f"fal job {status}: {sr.text}")
            time.sleep(self.poll_interval_s)
        else:
            raise FalError(f"fal job did not complete within {self.poll_timeout_s}s")

        # 3. Fetch result
        rr = client.get(result_url)
        if rr.status_code >= 400:
            raise FalError(f"fal result fetch failed: {rr.status_code} {rr.text}")
        body = rr.json()
        images = body.get("images") or []
        if not images:
            raise FalError(f"fal result has no images: {body}")
        image_url = images[0].get("url")
        if not image_url:
            raise FalError(f"fal result image has no url: {images[0]}")

        ir = client.get(image_url)
        if ir.status_code >= 400:
            raise FalError(f"image download failed: {ir.status_code}")
        return ir.content
