"""Render the Wiser Learner system blueprint onto a Miro board.

One-shot script. Reads MIRO_TOKEN and MIRO_BOARD_ID from env, then creates:
  - 4 frames (one per architectural layer)
  - one shape per component, colour-coded by build status
  - connectors for the canonical end-to-end episode flow

Run:
    python scripts/miro_blueprint.py

Idempotency: this script does NOT clean up prior runs. Run on an empty board,
or delete previously created items first via the Miro UI.

Status colour key (rendered on each shape):
    BUILT    light green  #C9F2C7
    SPEC     light yellow #FFF59D
    STUB     light orange #FFE0B2
    MISSING  light red    #FFCDD2
"""

from __future__ import annotations

import os
import sys
import time
import urllib.parse
from dataclasses import dataclass

import httpx

API_BASE = "https://api.miro.com/v2"

STATUS_COLOR = {
    "BUILT": "#C9F2C7",
    "SPEC": "#FFF59D",
    "STUB": "#FFE0B2",
    "MISSING": "#FFCDD2",
}

# ---------------------------------------------------------------------------
# Component model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Node:
    key: str  # short id used by connectors
    label: str  # text on the shape
    status: str  # BUILT | SPEC | STUB | MISSING
    layer: str  # governance | intelligence | pipeline | artefacts


# Order within each layer is left-to-right.
NODES: list[Node] = [
    # Layer 4 — governance
    Node("contract", "Contract\n(CONTRACT.md)", "BUILT", "governance"),
    Node("rubric", "Audit rubric", "BUILT", "governance"),
    Node("workflow", "Workflow rules", "BUILT", "governance"),
    Node("library", "Library\n(16 entries)", "BUILT", "governance"),
    Node("docs", "Architecture\n+ blueprint docs", "BUILT", "governance"),
    # Layer 3 — intelligence (agents + skills)
    Node("researcher", "Researcher\nagent", "BUILT", "intelligence"),
    Node("scripter", "Scripter\nagent", "BUILT", "intelligence"),
    Node("auditor_a", "Auditor\nagent", "BUILT", "intelligence"),
    Node("voicedir", "Voice director\nagent", "BUILT", "intelligence"),
    Node("visualdir", "Visual director\nagent", "BUILT", "intelligence"),
    Node("captioner", "Captioner\nagent", "BUILT", "intelligence"),
    Node("seo", "SEO\nagent", "BUILT", "intelligence"),
    Node("analyst", "Analyst\nagent", "BUILT", "intelligence"),
    Node("publisher_a", "Publisher\nagent", "BUILT", "intelligence"),
    Node("skill_libv", "Skill:\nlibrary-verify", "BUILT", "intelligence"),
    Node("skill_caud", "Skill:\ncontract-audit", "BUILT", "intelligence"),
    Node("skill_visd", "Skill:\nvisual-director", "BUILT", "intelligence"),
    Node("agent_runner", "agent_runner.py\n+ agents_run.py", "BUILT", "intelligence"),
    # Layer 2 — pipeline (deterministic Python)
    Node("audit", "audit.py", "BUILT", "pipeline"),
    Node("tts", "tts.py", "BUILT", "pipeline"),
    Node("captions_p", "captions.py", "BUILT", "pipeline"),
    Node("storyboard", "storyboard.py\n(schema + fallback)", "BUILT", "pipeline"),
    Node("visuals", "visuals.py\n+ providers registry", "BUILT", "pipeline"),
    Node("fal", "providers/fal.py", "BUILT", "pipeline"),
    Node("compositor", "compositor.py v0.2", "BUILT", "pipeline"),
    Node("youtube", "youtube.py", "BUILT", "pipeline"),
    Node("run_ep", "run_episode.py\n(orchestrator)", "BUILT", "pipeline"),
    Node("cli", "cli.py", "BUILT", "pipeline"),
    Node("cost_guard", "cost_guard.py", "BUILT", "pipeline"),
    Node("cache", "cache.py", "BUILT", "pipeline"),
    Node("analytics_p", "analytics.py", "BUILT", "pipeline"),
    Node("scripter_p", "agents_run.py\nrun_scripter()", "BUILT", "pipeline"),
    Node("seo_p", "agents_run.py\nrun_seo()", "BUILT", "pipeline"),
    # Layer 1 — artefacts (per episode)
    Node("brief", "brief.yaml\n(template)", "BUILT", "artefacts"),
    Node("script_md", "script.md", "BUILT", "artefacts"),
    Node("audit_json", "audit.json", "BUILT", "artefacts"),
    Node("voice_yaml", "voice.yaml", "BUILT", "artefacts"),
    Node("voice_wav", "voice.wav +\nvoice.json", "BUILT", "artefacts"),
    Node("captions_files", "captions.srt /\n.vtt / .json", "BUILT", "artefacts"),
    Node("comp_yaml", "composition.yaml", "BUILT", "artefacts"),
    Node("visuals_png", "visuals/*.png", "BUILT", "artefacts"),
    Node("episode_mp4", "episode.mp4", "BUILT", "artefacts"),
    Node("seo_yaml", "seo.yaml", "BUILT", "artefacts"),
    Node("meta_yaml", "meta.yaml", "BUILT", "artefacts"),
    Node("thumb", "thumbnail.png", "BUILT", "artefacts"),
    Node("receipt", "publish-receipt.json\n(needs YT keys)", "BUILT", "artefacts"),
    Node("metrics", "analytics/*.json\n(needs YT keys)", "BUILT", "artefacts"),
]

# Connectors describe the canonical episode flow + key dependencies.
# Each tuple is (source_key, target_key, label_or_None).
EDGES: list[tuple[str, str, str | None]] = [
    # research -> script
    ("library", "researcher", None),
    ("researcher", "skill_libv", "uses"),
    ("researcher", "scripter_p", "candidates"),
    ("scripter", "scripter_p", "system prompt"),
    ("scripter_p", "script_md", "writes"),
    # script -> audit
    ("script_md", "audit", None),
    ("audit", "audit_json", "writes"),
    ("auditor_a", "skill_caud", "uses"),
    ("agent_runner", "auditor_a", "invokes"),
    ("auditor_a", "audit_json", "agent block"),
    # audit -> tts
    ("audit_json", "voicedir", "gate=pass"),
    ("voicedir", "voice_yaml", "writes"),
    ("voice_yaml", "tts", "config"),
    ("script_md", "tts", "text"),
    ("tts", "voice_wav", "writes"),
    # captions
    ("voice_wav", "captions_p", None),
    ("script_md", "captions_p", None),
    ("captions_p", "captions_files", "writes"),
    ("captions_files", "captioner", "verifies"),
    # visuals
    ("voice_wav", "visualdir", "timings"),
    ("script_md", "visualdir", None),
    ("visualdir", "skill_visd", "uses"),
    ("agent_runner", "visualdir", "invokes"),
    ("visualdir", "comp_yaml", "writes"),
    ("storyboard", "comp_yaml", "fallback"),
    ("comp_yaml", "visuals", "manifest"),
    ("visuals", "fal", "calls"),
    ("fal", "cost_guard", "checks"),
    ("fal", "cache", "checks"),
    ("visuals", "visuals_png", "writes"),
    # composite
    ("visuals_png", "compositor", None),
    ("voice_wav", "compositor", None),
    ("captions_files", "compositor", None),
    ("comp_yaml", "compositor", None),
    ("compositor", "episode_mp4", "writes"),
    # SEO + publish
    ("script_md", "seo", None),
    ("seo", "seo_p", "system prompt"),
    ("seo_p", "seo_yaml", "writes"),
    ("seo_yaml", "meta_yaml", "feeds"),
    ("episode_mp4", "publisher_a", None),
    ("meta_yaml", "publisher_a", None),
    ("thumb", "publisher_a", None),
    ("publisher_a", "youtube", "drives"),
    ("youtube", "receipt", "writes"),
    # analytics loop
    ("receipt", "analytics_p", None),
    ("analytics_p", "metrics", "writes"),
    ("metrics", "analyst", None),
    ("analyst", "contract", "amendment\nproposal"),
    # orchestration
    ("cli", "run_ep", "invokes"),
    ("run_ep", "audit", None),
    ("run_ep", "tts", None),
    ("run_ep", "captions_p", None),
    ("run_ep", "visuals", None),
    ("run_ep", "compositor", None),
    # governance overlay
    ("contract", "audit", "enforces"),
    ("contract", "auditor_a", "judges against"),
    ("rubric", "audit", "rules"),
    ("rubric", "auditor_a", "rules"),
    ("brief", "scripter", "input"),
]

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

LAYER_ORDER = ["governance", "intelligence", "pipeline", "artefacts"]
LAYER_TITLE = {
    "governance": "LAYER 4 — GOVERNANCE (text)",
    "intelligence": "LAYER 3 — INTELLIGENCE (Claude agents + skills)",
    "pipeline": "LAYER 2 — PIPELINE (deterministic Python)",
    "artefacts": "LAYER 1 — ARTEFACTS (per-episode files)",
}

NODE_W = 220
NODE_H = 90
COL_GAP = 60
ROW_GAP = 40
LAYER_GAP = 220
LAYER_PAD_TOP = 80  # space inside frame for the title
LAYER_PAD_X = 40

ITEMS_PER_ROW = 6


def layout() -> tuple[dict[str, dict], list[dict]]:
    """Return (positions_by_key, frame_specs)."""
    positions: dict[str, dict] = {}
    frames: list[dict] = []
    cursor_y = 0.0

    for layer in LAYER_ORDER:
        nodes = [n for n in NODES if n.layer == layer]
        rows = (len(nodes) + ITEMS_PER_ROW - 1) // ITEMS_PER_ROW
        frame_w = ITEMS_PER_ROW * NODE_W + (ITEMS_PER_ROW - 1) * COL_GAP + 2 * LAYER_PAD_X
        frame_h = LAYER_PAD_TOP + rows * NODE_H + (rows - 1) * ROW_GAP + LAYER_PAD_X

        frame_x = 0.0  # frame centre x
        frame_y = cursor_y + frame_h / 2
        frames.append(
            {
                "layer": layer,
                "title": LAYER_TITLE[layer],
                "x": frame_x,
                "y": frame_y,
                "w": frame_w,
                "h": frame_h,
            }
        )

        # nodes are positioned in absolute board coords (not frame-relative)
        # frame top-left corner:
        tl_x = frame_x - frame_w / 2
        tl_y = cursor_y
        for i, node in enumerate(nodes):
            row = i // ITEMS_PER_ROW
            col = i % ITEMS_PER_ROW
            cx = tl_x + LAYER_PAD_X + NODE_W / 2 + col * (NODE_W + COL_GAP)
            cy = tl_y + LAYER_PAD_TOP + NODE_H / 2 + row * (NODE_H + ROW_GAP)
            positions[node.key] = {"x": cx, "y": cy}

        cursor_y = cursor_y + frame_h + LAYER_GAP

    return positions, frames


# ---------------------------------------------------------------------------
# Miro client
# ---------------------------------------------------------------------------


class Miro:
    def __init__(self, token: str, board_id: str) -> None:
        # Miro board IDs often end in '=' which must be percent-encoded in the path.
        encoded_board = urllib.parse.quote(board_id, safe="")
        self.client = httpx.Client(
            base_url=f"{API_BASE}/boards/{encoded_board}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    def _post(self, path: str, json: dict) -> dict:
        # Light retry for 429 / 5xx
        for attempt in range(5):
            r = self.client.post(path, json=json)
            if r.status_code < 300:
                return r.json()
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise RuntimeError(f"{r.status_code} {r.text}")
        raise RuntimeError(f"giving up after retries on {path}")

    def create_frame(self, *, title: str, x: float, y: float, w: float, h: float) -> str:
        body = {
            "data": {"title": title, "format": "custom"},
            "style": {"fillColor": "#F5F5F5"},
            "position": {"origin": "center", "x": x, "y": y},
            "geometry": {"width": w, "height": h},
        }
        return self._post("/frames", body)["id"]

    def create_shape(
        self,
        *,
        text: str,
        x: float,
        y: float,
        fill: str,
    ) -> str:
        body: dict = {
            "data": {"shape": "round_rectangle", "content": text},
            "style": {
                "fillColor": fill,
                "borderColor": "#1A1A1A",
                "borderWidth": 1.0,
                "fontSize": 14,
                "textAlign": "center",
                "textAlignVertical": "middle",
            },
            "position": {"origin": "center", "x": x, "y": y},
            "geometry": {"width": NODE_W, "height": NODE_H},
        }
        return self._post("/shapes", body)["id"]

    def create_connector(self, *, src_id: str, dst_id: str, caption: str | None) -> None:
        body: dict = {
            "startItem": {"id": src_id},
            "endItem": {"id": dst_id},
            "shape": "elbowed",
            "style": {
                "strokeColor": "#666666",
                "strokeWidth": 1.0,
                "endStrokeCap": "arrow",
            },
        }
        if caption:
            body["captions"] = [{"content": caption}]
        self._post("/connectors", body)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    token = os.environ.get("MIRO_TOKEN")
    board_id = os.environ.get("MIRO_BOARD_ID")
    if not token or not board_id:
        print("error: set MIRO_TOKEN and MIRO_BOARD_ID env vars", file=sys.stderr)
        return 2

    miro = Miro(token, board_id)
    positions, frames = layout()

    # Frames first (skip if MIRO_SKIP_FRAMES=1 so re-runs don't duplicate)
    skip_frames = os.environ.get("MIRO_SKIP_FRAMES") == "1"
    if not skip_frames:
        for f in frames:
            fid = miro.create_frame(title=f["title"], x=f["x"], y=f["y"], w=f["w"], h=f["h"])
            print(f"frame  {f['layer']:14} -> {fid}")
    else:
        print("MIRO_SKIP_FRAMES=1 — skipping frame creation")

    # Shapes (board-absolute coords, not parented to frames)
    shape_id_by_key: dict[str, str] = {}
    for node in NODES:
        pos = positions[node.key]
        text = f"<p><b>{node.label}</b></p><p style='font-size:11px;color:#555'>{node.status}</p>"
        sid = miro.create_shape(
            text=text,
            x=pos["x"],
            y=pos["y"],
            fill=STATUS_COLOR[node.status],
        )
        shape_id_by_key[node.key] = sid
        print(f"shape  {node.key:18} {node.status:7} -> {sid}")

    # Connectors
    for src, dst, caption in EDGES:
        if src not in shape_id_by_key or dst not in shape_id_by_key:
            print(f"skip connector: missing key {src} -> {dst}", file=sys.stderr)
            continue
        miro.create_connector(
            src_id=shape_id_by_key[src],
            dst_id=shape_id_by_key[dst],
            caption=caption,
        )
        print(f"edge   {src} -> {dst}{f'  [{caption}]' if caption else ''}")

    print("\ndone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
