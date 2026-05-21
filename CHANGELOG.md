# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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
