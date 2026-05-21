# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Geragogy Contract v1.0.0-draft (Part 3).** `contract/CONTRACT.md` and `contract/audit-rubric.md`. Eleven sections govern audience, editorial posture, script structure & pacing, forbidden patterns, voice & audio, visual & display, captions, AI/Claude content rules, CTAs, risk/safety, and compliance. Every clause is library-cited.
- **Maintenance items M-002, M-003, M-004** opened in `docs/maintenance.md` (patent-pending check, visual-spec tightening from licensed PDFs, voice character re-evaluation).
- **Pipeline scaffold v0.1.0 (Part 5).** Working contract auditor plus interface stubs for the rest of the pipeline:
  - `pipeline/audit.py` — deterministic checks for clauses C-1, C-3, C-4, C-9. 11 unit tests pass.
  - `pipeline/data/forbidden_patterns.yaml` — canonical machine-readable forbidden-phrase list (mirror of `contract/audit-rubric.md` §C-4).
  - `pipeline/cli.py` — `python -m pipeline.cli audit <script.md>` entry point; `tts`, `captions`, `composite`, `publish` subcommands stubbed.
  - `pipeline/run_episode.py` — orchestrator; failing audit blocks the rest of the pipeline.
  - `pipeline/tts.py`, `pipeline/captions.py`, `pipeline/compositor.py`, `pipeline/youtube.py` — typed interface stubs for downstream parts.
  - `agents/` — markdown specifications for scripter, auditor, researcher, voice-director, visual-director, captioner, compositor, seo, publisher, analyst.
  - `skills/contract-audit/` and `skills/library-verify/` — Claude skill stubs.
  - `mcp/README.md` — planned MCP servers (library, contract, youtube).
  - `episodes/_template/script.md` — script template conforming to the audit input schema.
  - `tests/test_audit.py`, `tests/test_forbidden_patterns.py` — 11 tests covering good/bad scripts and rubric integrity.
- **Library batch 04 — Digital interaction and older adults (Part 2).** Four triple-verified entries:
  - `L-013` Pradhan, Lazar & Findlater (2020). Use of intelligent voice assistants by older adults with low technology use.
  - `L-014` Knowles & Hanson (2018). Older adults' deployment of 'distrust'.
  - `L-015` Beneito-Montagut, Rosales & Fernández-Ardèvol (2022). Emerging Digital Inequalities.
  - `L-016` Chen et al. (2021). Barriers and design opportunities for voice assistants.
- **Workflow Rule 7** — right-sized review by change class. Library entries and pure-docs changes commit directly to `main`; contract, code, CI, and content remain under PR discipline.
- **Library status note.** Sixteen entries are sufficient warrant for drafting the Geragogy Contract (Part 3). Further batches are deferred until scripting surfaces specific spec-level needs.
- **Library batch 03 — Technology acceptance for older adults (Part 2).** Four triple-verified entries:
  - `L-009` Renaud & van Biljon (2008). Predicting technology acceptance and adoption by the elderly (STAM).
  - `L-010` Chen & Chan (2014). Gerontechnology acceptance: STAM empirically validated.
  - `L-011` Mitzner et al. (2010). Older adults talk technology.
  - `L-012` Hauk, Hüffmeier & Krumm (2018). Meta-analysis on age and technology acceptance.
- **Library batch 02 — CREATE / digital design for older adults (Part 2).** Five triple-verified entries:
  - `L-004` Czaja et al. (2006). Factors predicting the use of technology (CREATE).
  - `L-005` Czaja & Lee (2006). The impact of aging on access to technology.
  - `L-006` Charness & Boot (2009). Aging and Information Technology Use.
  - `L-007` Czaja, Boot, Charness & Rogers (2019). *Designing for Older Adults* (3rd ed.).
  - `L-008` McLaughlin & Pak (2020). *Designing Displays for Older Adults* (2nd ed.).
- `scripts/verify_doi.py` — lean Crossref-by-DOI verification helper used to confirm batch 02 sources.
- **Library batch 01 — Foundations (Part 2).** Three triple-verified entries:
  - `L-001` Knowles, Holton III, Swanson & Robinson (2020). *The Adult Learner* (9th ed.).
  - `L-002` Baltes (1997). On the incomplete architecture of human ontogeny (SOC).
  - `L-003` Formosa (2014). Lifelong Learning in Later Life.
- `library/INDEX.md` populated with batch 01 and a roadmap of pending batches 02–06.
- Initial enterprise-grade scaffold.
- README, BUSL-1.1 LICENSE, contributing/security/code-of-conduct policies.
- `pyproject.toml` with ruff/pytest/coverage config.
- `requirements.txt` and `requirements-dev.txt`.
- Pre-commit hooks: ruff, markdownlint, gitleaks, file hygiene.
- GitHub Actions CI workflow.
- GitHub Actions library-verification workflow (weekly).
- Issue templates: bug, library source proposal, contract amendment.
- Pull request template.
- Dependabot configuration.
- Architecture Decision Record 0001: runtime is GitHub Actions.
- `docs/architecture.md` capturing Part 1 — the 720° pipeline blueprint.
- `docs/workflow-rules.md` codifying the verify-before-deciding principle and
  five companion rules; surfaced from `README.md`.

[Unreleased]: https://github.com/smiles70/thewiserlearner/compare/HEAD...HEAD
