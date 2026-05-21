"""End-to-end episode orchestrator.

Runs the four production stages in order, gated by the contract auditor:

    1. audit      - pipeline.audit (deterministic; blocks on fail)
    2. tts        - pipeline.tts (network: Edge-TTS)
    3. captions   - pipeline.captions (best-effort; warns if stub)
    4. composite  - pipeline.compositor (ffmpeg)

A failing audit halts the entire run. Each stage's outputs land next to the
script. Use ``--from-stage`` to resume mid-pipeline (e.g. after fixing a
caption tweak you want to recomposite without re-running TTS).

CLI:
    python -m pipeline.run_episode episodes/E-001-foo/script.md
    python -m pipeline.run_episode episodes/E-001-foo/script.md --from-stage composite
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pipeline import compositor as compositor_mod
from pipeline import tts as tts_mod
from pipeline.audit import audit_script, write_audit_report

STAGES = ("audit", "tts", "captions", "composite")


def _print_stage(idx: int, name: str, msg: str) -> None:
    print(f"[{idx}/{len(STAGES)}] {name:9} {msg}")


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

    # Stage 2: TTS
    if start_idx <= 1:
        _print_stage(2, "tts", "synthesising voice ...")
        tts_result = tts_mod.synthesise(script_path, out_dir)
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
    elif captions_srt.is_file():
        captions_path = captions_srt

    # Stage 4: composite
    if start_idx <= 3:
        _print_stage(4, "composite", "rendering MP4 ...")
        comp = compositor_mod.composite(voice_wav, captions_path, script_path, out_dir)
        print(f"          video: {comp.video_path} ({comp.duration_seconds:.1f}s)")

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
    args = p.parse_args(argv)
    return run(Path(args.script).resolve(), from_stage=args.from_stage)


if __name__ == "__main__":
    raise SystemExit(main())
