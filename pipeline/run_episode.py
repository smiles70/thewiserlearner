"""End-to-end episode orchestrator.

In v0.1.0 this runs only the audit stage. Subsequent stages (tts, captions,
compositor, youtube) are stubbed and will be wired in by later parts.

The orchestrator's contract guarantee is simple: **a failing audit blocks the
remainder of the pipeline.** No TTS, no rendering, no upload happens until the
script is contract-compliant.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pipeline.audit import audit_script, write_audit_report


def run(script_path: Path, *, dry_run: bool = True) -> int:
    if not script_path.is_file():
        print(f"error: script not found: {script_path}", file=sys.stderr)
        return 2

    print(f"[1/5] auditing {script_path} ...")
    report = audit_script(script_path)
    out_dir = script_path.parent
    audit_target = write_audit_report(report, out_dir)
    print(f"      verdict: {report.verdict}  ({audit_target})")
    if report.verdict == "fail":
        print("BLOCKED: audit failed — fix the script and re-run.", file=sys.stderr)
        return 1

    if dry_run:
        print("[2/5] tts        — skipped (dry-run / stub)")
        print("[3/5] captions   — skipped (dry-run / stub)")
        print("[4/5] composite  — skipped (dry-run / stub)")
        print("[5/5] publish    — skipped (dry-run / stub)")
        return 0

    print("non-dry-run is not yet implemented in v0.1.0", file=sys.stderr)
    return 64


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="run_episode")
    p.add_argument("script", help="path to script.md")
    p.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="audit only; do not synthesise or upload (default in v0.1.0)",
    )
    args = p.parse_args(argv)
    return run(Path(args.script).resolve(), dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
