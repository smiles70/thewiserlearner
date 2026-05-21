"""Lean Crossref-by-DOI verifier for library candidate sources.

Usage:
    python scripts/verify_doi.py 10.1037/0882-7974.21.2.333 [more dois...]

Prints a compact, copy-pastable verification record for each DOI.
"""
from __future__ import annotations

import json
import sys
import urllib.request


def fetch(doi: str) -> dict:
    url = f"https://api.crossref.org/works/{doi}"
    req = urllib.request.Request(url, headers={"User-Agent": "thewiserlearner/0.1 (verify_doi)"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read()).get("message", {})


def first(seq, default=None):
    return seq[0] if seq else default


def show(doi: str) -> None:
    print(f"=== {doi} ===")
    try:
        m = fetch(doi)
    except Exception as e:
        print(f"  ERROR: {e}")
        return
    authors = "; ".join(
        f"{a.get('family','')}, {a.get('given','')}".strip(", ")
        for a in m.get("author", [])
    )
    editors = "; ".join(
        f"{a.get('family','')}, {a.get('given','')}".strip(", ")
        for a in m.get("editor", [])
    )
    year = first(first(m.get("issued", {}).get("date-parts", [[None]])) or [None])
    print(f"  TITLE:   {first(m.get('title'))}")
    print(f"  AUTHORS: {authors or '-'}")
    if editors:
        print(f"  EDITORS: {editors}")
    print(f"  YEAR:    {year}")
    print(f"  VENUE:   {first(m.get('container-title'))}")
    print(f"  VOL/ISS/PG: {m.get('volume','-')}/{m.get('issue','-')}/{m.get('page','-')}")
    print(f"  PUB:     {m.get('publisher')}")
    print(f"  TYPE:    {m.get('type')}")
    print(f"  ISSN:    {m.get('ISSN')}")
    print(f"  ISBN:    {m.get('ISBN')}")
    print(f"  DOI URL: https://doi.org/{m.get('DOI')}")
    print()


def main() -> int:
    for doi in sys.argv[1:]:
        show(doi)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
