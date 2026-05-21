# The Wiser Learner

> A fully automated, geragogy-governed YouTube production system for *Mynaani* —
> teaching AI and Claude to older adults with the dignity and pace they deserve.

[![CI](https://github.com/smiles70/thewiserlearner/actions/workflows/ci.yml/badge.svg)](https://github.com/smiles70/thewiserlearner/actions/workflows/ci.yml)
[![Library Verify](https://github.com/smiles70/thewiserlearner/actions/workflows/library-verify.yml/badge.svg)](https://github.com/smiles70/thewiserlearner/actions/workflows/library-verify.yml)
[![License: BUSL-1.1](https://img.shields.io/badge/license-BUSL--1.1-blue.svg)](./LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

---

## What this is

A production pipeline that:

1. Researches digital-learning and digital-interaction evidence relevant to older adults
   (geragogy), from peer-reviewed and dissertation-grade sources only.
2. Verifies every source three ways before allowing it to influence content.
3. Generates contract-compliant scripts, voice, captions, b-roll, video, thumbnails,
   and SEO metadata.
4. Publishes to YouTube and ingests analytics to evolve the contract over time.

Every decision in this repo is rooted in published evidence. No claim ships without a
citation. No source enters the library without triple verification.

## Who this is for

The channel speaks to older adults (65+) in the United States who want to learn AI
and Claude on their own terms. Caregivers and educators are not the primary audience.

## Workflow rules

Before contributing, read [`docs/workflow-rules.md`](./docs/workflow-rules.md).
The headline rule:

> When in doubt, check external sources. Don't guess. Don't rely on training
> alone. Find at least three references, then proceed with the best-in-class
> enterprise standard.

## Repo map

| Path | What lives here |
|---|---|
| [`library/`](./library) | Verified geragogy sources (Part 2) |
| [`contract/`](./contract) | The Geragogy Contract — the rulebook for every video (Part 3) |
| [`skills/`](./skills) | Claude Skills used by the pipeline (Part 5) |
| [`.claude/agents/`](./.claude/agents) | Claude Code sub-agents (Part 5) |
| [`mcp/`](./mcp) | Custom MCP servers for OpenAlex, Crossref, YouTube (Part 5) |
| [`pipeline/`](./pipeline) | The 14 stage scripts (Part 5) |
| [`episodes/`](./episodes) | Per-episode work directories |
| [`analytics/`](./analytics) | SQLite database of performance data |
| [`docs/`](./docs) | Architecture docs + Architecture Decision Records |
| [`tests/`](./tests) | Test suite |

## Quickstart

> Prerequisites: Python 3.11+, `ffmpeg` on PATH, a GitHub account with this repo cloned.

```bash
python -m venv .venv
. .venv/Scripts/activate            # PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
pre-commit install
pytest
```

## Status

| Part | Status |
|---|---|
| Part 1 — 720° Pipeline Blueprint | ✅ Complete ([`docs/architecture.md`](./docs/architecture.md)) |
| Part 2 — Elite Geragogy Library v1 | ⏳ In progress ([`library/INDEX.md`](./library/INDEX.md)) |
| Part 3 — Geragogy Contract v1 | 🔒 Pending Part 2 |
| Part 4 — Three pilot scripts | 🔒 Pending Part 3 |
| Part 5 — Runnable pipeline | 🔒 Pending Part 4 |

## License

[BUSL-1.1](./LICENSE). Source-available; commercial use restricted until the Change Date
(2030-05-21), after which the license converts automatically to Apache 2.0.

If you are interested in a commercial-use license before the Change Date,
please open an issue.

## Patent notice

A provisional patent application has been filed covering the curriculum design and
front-end app design used in *Mynaani*. Patent pending.

## Contributing

See [`CONTRIBUTING.md`](./CONTRIBUTING.md). The two highest-leverage contributions are
proposing new library sources and proposing contract amendments — both have dedicated
issue templates.

## Security

See [`SECURITY.md`](./SECURITY.md).
