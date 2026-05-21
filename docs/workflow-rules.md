# Workflow Rules

These are non-negotiable operating principles for everyone (humans and AI agents)
contributing to this project. They are listed in priority order.

## Rule 1 — Verify before deciding

> **When in doubt, check external sources. Don't guess. Don't rely on training
> alone. Find at least three references, then proceed with the best-in-class
> enterprise standard.**

This rule applies to every non-trivial decision: architecture, tooling choices,
library inclusion, contract amendments, naming, copy, and editorial calls.

**How it is applied:**

1. State the decision being made.
2. Identify at least **three independent, reputable sources** (primary
   documentation, peer-reviewed evidence, or recognised industry standards).
3. Record the sources where the decision lives:
   - Architecture/tooling decisions → ADR in `docs/adr/`.
   - Content decisions → linked from `contract/decisions/`.
   - Library entries → in the entry's own front-matter.
4. Choose the best-in-class enterprise standard implied by the evidence.
5. If the three sources disagree, gather more until the picture is clear, or
   document the unresolved tension explicitly.

Personal preference, "feels right", or training-data recall are insufficient
grounds for any decision in this repo.

## Rule 2 — The Contract is supreme

The Geragogy Contract (`contract/CONTRACT.md`) governs every production decision.
If a pipeline choice conflicts with the Contract, the Contract wins. Amend the
Contract through the documented amendment process (see
[`.github/ISSUE_TEMPLATE/contract_amendment.md`](../.github/ISSUE_TEMPLATE/contract_amendment.md)).

## Rule 3 — No claim without a citation

Every factual statement that reaches a viewer must be traceable to a verified
entry in `library/`. Extrapolation, plausible-sounding inference, and
"common knowledge" are not citations.

## Rule 4 — No placeholders in the library

A source that cannot be triple-verified (OpenAlex + Crossref + publisher page;
title + first author + year must agree) is discarded, not approximated. Better a
smaller, rigorously verified corpus than a larger one with unstable foundations.

## Rule 5 — Empathetic, never apologetic

The audience is older adults — competent, accomplished people who happen to be
new to a specific technology. Tone in scripts, copy, commits, and PR comments
must reflect that. Condescension, ageist framing, and apologetic posture are
defects.

## Rule 6 — Small, reviewable change sets

Pull requests stay under ~200 changed lines or ~10 library entries, whichever
limit comes first. Evidence: small PRs are approved roughly three times faster
and produce higher review quality (see
[Propelcode 2024 study](https://www.propelcode.ai/blog/pr-size-impact-code-review-quality-data-study)
and [BSSW.io — Pull Request Size Matters](https://bssw.io/items/pull-request-size-matters)).
Larger logical units are split into a stacked series of PRs.

## Rule 7 — Right-sized review for the change class

Not every change deserves the same ceremony. Branch protection is deferred (see
[`docs/maintenance.md`](./maintenance.md) M-001), so this rule governs by
convention.

| Change class                                            | Workflow                                                                                                            |
|---------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------|
| **Library entries** (`library/L-*.md`, `library/INDEX.md`, batch `CHANGELOG.md` lines) | Commit **directly to `main`** in batches. Each batch is a single commit; the commit message lists every L-id added. Triple-verification is recorded in the entry itself. |
| **Documentation only** (`README.md`, `docs/**` typo/wording) | Commit directly to `main`.                                                                                          |
| **Contract changes** (`contract/**`)                    | **Pull request required.** Must cite at least one library entry per material clause changed.                        |
| **Pipeline code, CI, tests, dependencies**              | **Pull request required.** Local `ruff format --check`, `ruff check`, and `pytest` must pass before push.           |
| **Episode scripts and assets** (`episodes/**`)          | **Pull request required.** Contract-compliance audit must pass.                                                     |

Rationale: library entries are pure evidence records that cannot affect runtime
behaviour. Their review is the triple-verification embedded in the entry itself,
not a second human gate. Code, contract, and content can break things and stay
under PR discipline.
