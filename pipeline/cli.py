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

from pipeline import tts as tts_mod
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

    for name in ("captions", "composite", "publish"):
        s = sub.add_parser(name, help=f"{name} (stubbed in v0.1.0)")
        s.set_defaults(func=_not_implemented(name))

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
