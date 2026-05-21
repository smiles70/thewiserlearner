"""Command-line entry points for the pipeline.

Subcommands (current):
    audit       — run the contract auditor against a script.md and write audit.json

Subcommands (stubbed for later parts):
    tts         — synthesise voice from a passing script
    captions    — generate SRT captions from voice audio
    composite   — assemble final video from voice + b-roll + captions
    publish     — upload to YouTube

Usage:
    python -m pipeline.cli audit episodes/E-001-*/script.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pipeline import compositor as compositor_mod
from pipeline import run_episode as run_episode_mod
from pipeline import tts as tts_mod
from pipeline import youtube as youtube_mod
from pipeline.audit import audit_script, write_audit_report


def cmd_audit(args: argparse.Namespace) -> int:
    script_path = Path(args.script).resolve()
    if not script_path.is_file():
        print(f"error: script not found: {script_path}", file=sys.stderr)
        return 2
    report = audit_script(script_path)
    out_dir = script_path.parent
    target = write_audit_report(report, out_dir)
    print(f"audit verdict: {report.verdict}")
    print(f"audit report:  {target}")
    if args.verbose:
        print(json.dumps(report.to_dict(), indent=2))
    return 0 if report.verdict == "pass" else 1


def cmd_tts(args: argparse.Namespace) -> int:
    script_path = Path(args.script).resolve()
    if not script_path.is_file():
        print(f"error: script not found: {script_path}", file=sys.stderr)
        return 2
    out_dir = script_path.parent
    result = tts_mod.synthesise(
        script_path, out_dir, voice=args.voice, rate=args.rate, pitch=args.pitch
    )
    print(f"voice:    {result.audio_path}")
    print(f"manifest: {result.timing_manifest_path}")
    print(f"duration: {result.duration_seconds:.2f}s")
    if result.integrated_lufs is not None:
        print(f"loudness: {result.integrated_lufs:.2f} LUFS, peak {result.true_peak_dbtp:.2f} dBTP")
    return 0


def cmd_composite(args: argparse.Namespace) -> int:
    script_path = Path(args.script).resolve()
    voice_path = Path(args.voice).resolve()
    captions_srt = Path(args.captions).resolve() if args.captions else None
    if not script_path.is_file() or not voice_path.is_file():
        print("error: script and voice are required", file=sys.stderr)
        return 2
    if captions_srt is not None and not captions_srt.is_file():
        print(f"error: captions not found: {captions_srt}", file=sys.stderr)
        return 2
    out_dir = script_path.parent
    result = compositor_mod.composite(voice_path, captions_srt, script_path, out_dir)
    print(f"video:    {result.video_path}")
    print(f"duration: {result.duration_seconds:.2f}s")
    return 0


def cmd_publish(args: argparse.Namespace) -> int:
    script_path = Path(args.script).resolve()
    if not script_path.is_file():
        print(f"error: script not found: {script_path}", file=sys.stderr)
        return 2
    out_dir = script_path.parent
    video = Path(args.video) if args.video else out_dir / "episode.mp4"
    meta = Path(args.meta) if args.meta else out_dir / "meta.yaml"
    thumb = Path(args.thumbnail) if args.thumbnail else None
    if not video.is_file():
        print(f"error: video not found: {video}", file=sys.stderr)
        return 2
    if not meta.is_file():
        print(f"error: meta not found: {meta}", file=sys.stderr)
        return 2
    result = youtube_mod.publish(video, meta, thumbnail_path=thumb)
    print(f"published: {result.url}  ({result.privacy_status})")
    return 0


def cmd_run_episode(args: argparse.Namespace) -> int:
    return run_episode_mod.run(Path(args.script).resolve(), from_stage=args.from_stage)


def _not_implemented(name: str):
    def _run(_args: argparse.Namespace) -> int:
        print(f"`{name}` is stubbed in v0.1.0; arrives in a later part.", file=sys.stderr)
        return 64

    return _run


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pipeline", description="The Wiser Learner pipeline.")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("audit", help="run the contract auditor on a script.md")
    a.add_argument("script", help="path to script.md")
    a.add_argument("-v", "--verbose", action="store_true")
    a.set_defaults(func=cmd_audit)

    t = sub.add_parser("tts", help="synthesise voice.wav from a contract-passing script")
    t.add_argument("script", help="path to script.md")
    t.add_argument("--voice", default=tts_mod.DEFAULT_VOICE)
    t.add_argument("--rate", default=tts_mod.DEFAULT_RATE)
    t.add_argument("--pitch", default=tts_mod.DEFAULT_PITCH)
    t.set_defaults(func=cmd_tts)

    co = sub.add_parser("composite", help="render episode.mp4 from script + voice + captions")
    co.add_argument("script", help="path to script.md")
    co.add_argument("--voice", required=True, help="path to voice.wav from pipeline.tts")
    co.add_argument("--captions", default=None, help="optional path to captions.srt")
    co.set_defaults(func=cmd_composite)

    pu = sub.add_parser("publish", help="upload episode.mp4 to YouTube")
    pu.add_argument("script", help="path to script.md")
    pu.add_argument("--video", default=None, help="path to episode.mp4 (default: next to script)")
    pu.add_argument("--meta", default=None, help="path to meta.yaml (default: next to script)")
    pu.add_argument("--thumbnail", default=None, help="optional path to thumbnail PNG")
    pu.set_defaults(func=cmd_publish)

    re = sub.add_parser(
        "run", help="run the full pipeline end-to-end (audit -> tts -> captions -> composite)"
    )
    re.add_argument("script", help="path to script.md")
    re.add_argument(
        "--from-stage",
        choices=run_episode_mod.STAGES,
        default="audit",
        help="resume from this stage",
    )
    re.set_defaults(func=cmd_run_episode)

    for name in ("captions",):
        s = sub.add_parser(name, help=f"{name} (stubbed until pipeline/captions PR merges)")
        s.set_defaults(func=_not_implemented(name))

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
