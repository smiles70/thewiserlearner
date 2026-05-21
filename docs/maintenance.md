# Deferred Maintenance

Items that are not blocking but should be addressed when time permits. Each item
includes the rationale for deferral and the trigger that should re-prioritise it.

## Open

### M-001 — Enable branch protection on `main`

- **Status:** Deferred 2026-05-21.
- **What:** Configure a GitHub branch ruleset for `main` requiring PR, status
  checks (`lint-and-test (3.11)`, `lint-and-test (3.12)`, `markdownlint`,
  `gitleaks`), linear history, and no force-push.
- **Why deferred:** Sole maintainer at v0; PR-per-batch workflow (Rule 6) is
  followed by convention. Branch protection is best practice but not technically
  required at single-maintainer scale.
- **Re-prioritise when:** A second contributor is added, OR the first publicly
  visible production video ships, OR any near-miss occurs (accidental direct push
  of a non-trivial change).
- **How:** Settings → Branches → Add ruleset. Five clicks, ~60 seconds.

### M-002 — Verify Mynaani USPTO patent-pending status before first publish

- **Status:** Open 2026-05-21.
- **Source:** `contract/CONTRACT.md` C-9.3.
- **What:** Confirm current patent-pending status on USPTO. If lapsed, amend
  C-9.3 in a contract PR before any episode that mentions Mynaani ships.
- **Re-prioritise when:** Before the first pilot is finalised for upload.

### M-003 — Tighten visual/typography specs after page-level PDF verification

- **Status:** Open 2026-05-21.
- **Source:** `contract/CONTRACT.md` C-6.2, C-6.6, C-7.2, C-7.3; library entries
  L-007, L-008.
- **What:** Once licensed PDFs of *Designing for Older Adults* (3e) and
  *Designing Displays for Older Adults* (2e) are obtained, extract specific
  numbers and amend the contract to be stricter where the evidence supports it.
  Loosening any existing spec is forbidden.
- **Re-prioritise when:** Licensed PDFs are in hand, or when a production
  decision actually needs a number the contract does not yet supply.

### M-004 — Re-evaluate voice character (C-5.1) after three pilots

- **Status:** Open 2026-05-21.
- **Source:** `contract/CONTRACT.md` C-5.1.
- **What:** Collect viewer signal (comments, retention curves, returning-viewer
  rate) across the first three pilots and ≥ 3 weeks of analytics, then decide
  whether to keep, replace, or A/B the warm mid-50s female voice.
- **Re-prioritise when:** Three pilots have shipped and three weeks of
  analytics are available.

## Closed

_None yet._
