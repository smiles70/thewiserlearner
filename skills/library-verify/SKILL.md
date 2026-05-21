---
name: library-verify
description: Triple-verify a candidate source against OpenAlex, Crossref, and the publisher landing page.
inputs:
  - candidate metadata (title, first author, year, DOI if known)
outputs:
  - verification record for inclusion in a library/L-*.md front matter
---

# library-verify skill

For a candidate source, produce a verification record matching the
`verification:` block used in existing `library/L-*.md` files.

## Process

1. If a DOI is provided, fetch the canonical metadata from Crossref via
   `scripts/verify_doi.py`. Compare title, first author, year.
2. Look up the work in OpenAlex by DOI (or by title+author if no DOI). Compare
   title, first author, year.
3. Resolve the DOI URL (`https://doi.org/<doi>`) and confirm it 200s to a
   publisher landing page whose title and authors match.
4. If any of the three checks disagree, the candidate is rejected; emit a
   `status: rejected` record with the discrepancy noted.

## Output

```yaml
openalex: { id: "...", status: confirmed, matches: [title, first_author, year] }
crossref: { doi: "...", status: confirmed, matches: [title, first_author, year, venue, ...] }
publisher_page: { status: confirmed_via_doi_redirect, url: "..." }
verified_on: "YYYY-MM-DD"
```
