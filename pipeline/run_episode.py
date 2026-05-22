"""End-to-end episode orchestrator.

Runs the five production stages in order, gated by the contract auditor:

    1. audit      - pipeline.audit (deterministic; blocks on fail)
    2. tts        - pipeline.tts (network: Edge-TTS)
    3. captions   - pipeline.captions (best-effort; warns if stub)
    4. visuals    - pipeline.visuals (renders per-beat backgrounds; offline by default)
    5. composite  - pipeline.compositor (ffmpeg)

A failing audit halts the entire run. Each stage's outputs land next to the
script. Use ``--from-stage`` to resume mid-pipeline (e.g. after fixing a
caption tweak you want to recomposite without re-running TTS).

The visuals stage produces:
  - ``composition.yaml`` (the storyboard manifest; uses default_composition
    if one is not already present next to the script)
  - ``visuals/<beat>.png`` (one background per beat)
  - ``segments/<beat>[_step_N].png`` (titled cards consumed by the compositor)

CLI:
    python -m pipeline.run_episode episodes/E-001-foo/script.md
    python -m pipeline.run_episode episodes/E-001-foo/script.md --from-stage composite
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml

from pipeline import compositor as compositor_mod
from pipeline import storyboard as storyboard_mod
from pipeline import tts as tts_mod
from pipeline import visuals as visuals_mod
from pipeline.audit import audit_script, write_audit_report

STAGES = ("audit", "tts", "captions", "visuals", "composite")

# Filenames the agent stages may produce alongside the script.
VOICE_YAML = "voice.yaml"
COMPOSITION_YAML = "composition.yaml"
SEO_YAML = "seo.yaml"
AUDITOR_SUBJECTIVE_JSON = "auditor-subjective.json"
CAPTIONER_VERDICT_JSON = "captioner-verdict.json"
MOCKS_DIRNAME = "_mocks"


def _print_stage(idx: int, name: str, msg: str) -> None:
    print(f"[{idx}/{len(STAGES)}] {name:9} {msg}")


def _agents_enabled() -> bool:
    """True iff the user explicitly opted in via env or CLI.

    Set by ``--with-agents`` (which exports ``RUN_EPISODE_AGENTS=1``).
    Without the opt-in, all agent stages no-op so the pipeline runs offline.
    """
    return os.environ.get("RUN_EPISODE_AGENTS") == "1"


def _load_mock(out_dir: Path, role: str) -> dict[str, Any] | None:
    """Return canned mock response for `role` from ``_mocks/<role>.json``."""
    path = out_dir / MOCKS_DIRNAME / f"{role}.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"      WARN: {path} not valid JSON: {exc}", file=sys.stderr)
        return None


def _maybe_run_voice_director(script_path: Path, out_dir: Path) -> None:
    """If agents are enabled and no voice.yaml exists yet, generate one."""
    target = out_dir / VOICE_YAML
    if target.is_file() or not _agents_enabled():
        return
    from pipeline import agents_run as agents_mod
    from pipeline.voice_config import write_voice_config

    cfg = agents_mod.run_voice_director(
        script_text=script_path.read_text(encoding="utf-8"),
        episode_id=script_path.parent.name,
        mock_response=_load_mock(out_dir, "voice-director"),
    )
    write_voice_config(cfg, target)
    print(f"          agent: voice-director wrote {target.name}")


def _voice_kwargs_from_yaml(out_dir: Path) -> dict[str, str]:
    """Translate voice.yaml (if present) into tts.synthesise kwargs."""
    target = out_dir / VOICE_YAML
    if not target.is_file():
        return {}
    from pipeline.voice_config import load_voice_config

    cfg = load_voice_config(target)
    return {"voice": cfg.voice, "rate": cfg.rate, "pitch": cfg.pitch}


def _maybe_run_auditor_subjective(script_path: Path, out_dir: Path) -> None:
    if not _agents_enabled():
        return
    target = out_dir / AUDITOR_SUBJECTIVE_JSON
    if target.is_file():
        return
    from pipeline import agents_run as agents_mod

    repo = Path(__file__).resolve().parent.parent
    contract_text = (repo / "contract" / "CONTRACT.md").read_text(encoding="utf-8")
    rubric = (repo / "contract" / "AUDIT-RUBRIC.md")
    rubric_text = rubric.read_text(encoding="utf-8") if rubric.is_file() else ""
    report = agents_mod.run_auditor_subjective(
        script_text=script_path.read_text(encoding="utf-8"),
        contract_text=contract_text,
        audit_rubric_text=rubric_text,
        episode_id=script_path.parent.name,
        mock_response=_load_mock(out_dir, "auditor-subjective"),
    )
    target.write_text(json.dumps(report.model_dump(mode="json"), indent=2), encoding="utf-8")
    print(f"          agent: auditor-subjective verdict={report.overall} -> {target.name}")
    if report.overall == "fail":
        print("BLOCKED: auditor-subjective failed.", file=sys.stderr)
        raise SystemExit(1)


def _maybe_run_captioner_verify(
    captions_path: Path | None, script_path: Path, out_dir: Path
) -> None:
    if not _agents_enabled() or captions_path is None or not captions_path.is_file():
        return
    target = out_dir / CAPTIONER_VERDICT_JSON
    if target.is_file():
        return
    from pipeline import agents_run as agents_mod

    repo = Path(__file__).resolve().parent.parent
    contract_text = (repo / "contract" / "CONTRACT.md").read_text(encoding="utf-8")
    report = agents_mod.run_captioner_verify(
        captions_srt=captions_path.read_text(encoding="utf-8"),
        script_text=script_path.read_text(encoding="utf-8"),
        contract_c7_excerpt=contract_text,
        episode_id=script_path.parent.name,
        mock_response=_load_mock(out_dir, "captioner"),
    )
    target.write_text(json.dumps(report.model_dump(mode="json"), indent=2), encoding="utf-8")
    print(f"          agent: captioner verdict={report.overall} -> {target.name}")


def _maybe_run_seo(script_path: Path, out_dir: Path) -> None:
    if not _agents_enabled():
        return
    target = out_dir / SEO_YAML
    if target.is_file():
        return
    from pipeline import agents_run as agents_mod
    from pipeline.seo_meta import write_seo_meta

    meta = agents_mod.run_seo(
        script_text=script_path.read_text(encoding="utf-8"),
        episode_id=script_path.parent.name,
        mock_response=_load_mock(out_dir, "seo"),
    )
    write_seo_meta(meta, target)
    print(f"          agent: seo wrote {target.name}")


def _run_captions(script_path: Path, voice_manifest: Path, out_dir: Path) -> Path | None:
    """Best-effort captions: returns SRT path or None if module is stubbed."""
    try:
        from pipeline import captions as captions_mod
    except ImportError:  # pragma: no cover
        return None
    try:
        result = captions_mod.generate(script_path, voice_manifest, out_dir)
        return result.srt_path
    except NotImplementedError:
        print("      WARNING: captions module is stubbed; skipping captions stage")
        return None


def _maybe_run_visual_director(
    script_path: Path,
    voice_manifest: Path,
    out_dir: Path,
) -> None:
    """If agents are enabled and no composition.yaml exists, build one."""
    target = out_dir / COMPOSITION_YAML
    if target.is_file() or not _agents_enabled():
        return
    from pipeline import agents_run as agents_mod

    timings: dict[str, Any] = {}
    if voice_manifest.is_file():
        try:
            timings = json.loads(voice_manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            timings = {}
    comp = agents_mod.run_visual_director(
        script_text=script_path.read_text(encoding="utf-8"),
        voice_timings=timings,
        episode_id=script_path.parent.name,
        mock_response=_load_mock(out_dir, "visual-director"),
    )
    target.write_text(
        yaml.safe_dump(comp.model_dump(mode="json"), sort_keys=False),
        encoding="utf-8",
    )
    print(f"          agent: visual-director wrote {target.name}")


def _load_or_build_composition(
    script_path: Path,
    voice_manifest: Path,
    out_dir: Path,
) -> storyboard_mod.Composition:
    """Load `composition.yaml` next to the script if present, else build the
    deterministic default. Always re-writes the resolved composition to disk
    so downstream tooling (review skill, contract audit) sees a single
    canonical artefact."""
    comp_path = out_dir / COMPOSITION_YAML
    if comp_path.is_file():
        comp = storyboard_mod.load_composition(comp_path)
    else:
        comp = storyboard_mod.default_composition(script_path, voice_manifest)
        comp_path.write_text(
            yaml.safe_dump(comp.model_dump(mode="json"), sort_keys=False),
            encoding="utf-8",
        )
    return comp


def run(script_path: Path, *, from_stage: str = "audit") -> int:
    if from_stage not in STAGES:
        print(f"error: --from-stage must be one of {STAGES}", file=sys.stderr)
        return 2
    if not script_path.is_file():
        print(f"error: script not found: {script_path}", file=sys.stderr)
        return 2

    out_dir = script_path.parent
    start_idx = STAGES.index(from_stage)
    voice_wav = out_dir / "voice.wav"
    voice_json = out_dir / "voice.json"
    captions_srt = out_dir / "captions.srt"

    # Stage 1: audit
    if start_idx <= 0:
        _print_stage(1, "audit", f"running on {script_path.name} ...")
        report = audit_script(script_path)
        audit_target = write_audit_report(report, out_dir)
        print(f"          verdict: {report.verdict}  ({audit_target})")
        if report.verdict == "fail":
            print("BLOCKED: audit failed - fix the script and re-run.", file=sys.stderr)
            return 1

        _maybe_run_auditor_subjective(script_path, out_dir)

    # Stage 2: TTS
    if start_idx <= 1:
        _maybe_run_voice_director(script_path, out_dir)
        _print_stage(2, "tts", "synthesising voice ...")
        tts_kwargs = _voice_kwargs_from_yaml(out_dir)
        tts_result = tts_mod.synthesise(script_path, out_dir, **tts_kwargs)
        print(f"          voice: {tts_result.audio_path} ({tts_result.duration_seconds:.1f}s)")
        voice_wav = tts_result.audio_path
        voice_json = tts_result.timing_manifest_path
    elif not voice_wav.is_file():
        print(f"error: --from-stage={from_stage} but {voice_wav} missing", file=sys.stderr)
        return 2

    # Stage 3: captions (best effort)
    captions_path: Path | None = None
    if start_idx <= 2:
        _print_stage(3, "captions", "generating SRT/VTT ...")
        captions_path = _run_captions(script_path, voice_json, out_dir)
        if captions_path:
            print(f"          srt:   {captions_path}")
        _maybe_run_captioner_verify(captions_path, script_path, out_dir)
    elif captions_srt.is_file():
        captions_path = captions_srt

    # Stage 4: visuals (composition.yaml + per-beat backgrounds)
    composition: storyboard_mod.Composition | None = None
    visuals_results: dict[str, visuals_mod.VisualResult] | None = None
    if start_idx <= 3:
        _print_stage(4, "visuals", "rendering per-beat backgrounds ...")
        if not voice_json.is_file():
            print(f"error: visuals stage needs {voice_json}", file=sys.stderr)
            return 2
        _maybe_run_visual_director(script_path, voice_json, out_dir)
        composition = _load_or_build_composition(script_path, voice_json, out_dir)
        from pipeline.providers import get_provider

        provider = get_provider()
        visuals_results = visuals_mod.generate_all(composition, out_dir, provider=provider)
        print(f"          beats: {len(composition.beats)}  cards: {len(visuals_results)}")
    elif (out_dir / "composition.yaml").is_file():
        composition = storyboard_mod.load_composition(out_dir / "composition.yaml")
        # The composite stage will re-derive segment cards; we don't need
        # to re-render backgrounds here. We still need a visuals dict
        # pointing at on-disk PNGs.
        visuals_dir = out_dir / "visuals"
        visuals_results = {
            b.beat: visuals_mod.VisualResult(
                beat_name=b.beat,
                image_path=visuals_dir / f"{b.beat}.png",
                width=visuals_mod.CARD_WIDTH,
                height=visuals_mod.CARD_HEIGHT,
            )
            for b in composition.beats
        }

    # Stage 5: composite
    if start_idx <= 4:
        _print_stage(5, "composite", "rendering MP4 ...")
        if composition is None or visuals_results is None:
            # Fall back to v0.1 single-card path. Keeps the pipeline runnable
            # even if someone deletes the visuals output between stages.
            print("          v0.1 fallback: single-card composite")
            comp = compositor_mod.composite(voice_wav, captions_path, script_path, out_dir)
            print(f"          video: {comp.video_path} ({comp.duration_seconds:.1f}s)")
        else:
            comp_v2 = compositor_mod.composite_with_composition(
                voice_wav,
                captions_path,
                composition,
                visuals_results,
                voice_json,
                out_dir,
            )
            print(
                f"          video: {comp_v2.video_path} "
                f"({comp_v2.duration_seconds:.1f}s, {comp_v2.segment_count} segments)"
            )
        _maybe_run_seo(script_path, out_dir)

    print("\nepisode build complete.")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="run_episode", description=__doc__.split("\n", 1)[0])
    p.add_argument("script", help="path to script.md")
    p.add_argument(
        "--from-stage",
        choices=STAGES,
        default="audit",
        help="resume from this stage (default: audit, i.e. full pipeline)",
    )
    p.add_argument(
        "--with-agents",
        action="store_true",
        help=(
            "Enable agent stages (visual-director, voice-director, auditor-subjective, "
            "captioner-verify, seo). Requires ANTHROPIC_API_KEY or mock responses "
            "under episodes/<id>/_mocks/*.json with AGENT_RUNNER_MOCK=1."
        ),
    )
    args = p.parse_args(argv)
    if args.with_agents:
        os.environ["RUN_EPISODE_AGENTS"] = "1"
    return run(Path(args.script).resolve(), from_stage=args.from_stage)


if __name__ == "__main__":
    raise SystemExit(main())
