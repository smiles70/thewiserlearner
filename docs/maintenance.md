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

## Closed

_None yet._
