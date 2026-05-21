# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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
