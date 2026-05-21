# Contributing to The Wiser Learner

Thanks for your interest. This project has unusually strict standards because the
content it produces is consumed by older adults, and because every claim must be
defensible against the published literature.

## Two contributions matter most

### 1. Propose a new library source

Use the [`library_source` issue template](./.github/ISSUE_TEMPLATE/library_source.md).

A library source must be:

- A peer-reviewed paper, PhD dissertation, university research report, or a
  reputable government / multilateral organisation report.
- Triple-verifiable: title, first author, year must agree between OpenAlex,
  Crossref, and the publisher landing page.
- Retrievable (HTTP-200 reachable, either via DOI or a stable URL).
- Directly relevant to digital learning or digital interaction for older adults.

We do not accept blog posts, op-eds, vendor whitepapers, or generative-AI summaries.

### 2. Propose a contract amendment

Use the [`contract_amendment` issue template](./.github/ISSUE_TEMPLATE/contract_amendment.md).

A contract amendment must cite at least one library source that supports the
proposed rule. Personal preference is not enough.

## Development setup

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -r requirements-dev.txt
pre-commit install
pytest
```

## Branch / commit conventions

- Branch names: `kind/short-slug` where `kind` is one of `feat`, `fix`, `library`,
  `contract`, `docs`, `chore`.
- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/).
  Examples:
  - `library: add Czaja & Rogers 2019 designing-for-older-adults`
  - `contract: ratify voice gender and apparent age (decision/0007)`
  - `pipeline: implement stage_06_tts with edge-tts backend`

## Pull request checklist

- [ ] `pre-commit run --all-files` passes locally.
- [ ] `pytest` passes locally.
- [ ] If library entry added: triple-verification recorded in the entry.
- [ ] If contract amendment: linked to at least one library source.
- [ ] `CHANGELOG.md` updated under `[Unreleased]`.

## Code review

The maintainer is `@smiles70` (see [`CODEOWNERS`](./.github/CODEOWNERS)). All PRs
require maintainer approval until a second maintainer is added.
