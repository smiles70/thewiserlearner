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

    for name in ("tts", "captions", "composite", "publish"):
        s = sub.add_parser(name, help=f"{name} (stubbed in v0.1.0)")
        s.set_defaults(func=_not_implemented(name))

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
