---
name: scripter
description: Draft an 8-beat episode script from a brief and verified library entries; cite the contract; never quote unverified sources.
inputs:
  - brief (Brief schema from pipeline.brief)
  - library_entries (markdown bodies of cited L-* files)
  - contract_excerpt (relevant sections of CONTRACT.md)
outputs:
  - script.md as front_matter + body_markdown (matches ScripterOutput)
contract_clauses:
  - "C-1.*"
  - "C-2.*"
  - "C-3.*"
  - "C-4.*"
  - "C-8.*"
  - "C-9.*"
  - "C-10.*"
---

# scripter skill

You draft a single episode script. Your output is a JSON object with two
fields: `front_matter` (a YAML-compatible dict) and `body_markdown` (the
beat-by-beat script body).

## Process

1. Read the brief. Note: `id`, `title`, `topic`, `target_capability`,
   `target_runtime_seconds`, `level`, `library_refs`.
2. Read the contract excerpt. Internalise:
   - **C-3.x** the eight required beats in canonical order:
     `hook → acknowledge → why → show → walkthrough → recover → recap → outro`.
   - **C-3.2** mean speech rate 110–120 wpm; total words ≈ runtime_seconds × 1.92.
   - **C-4.\***: forbidden patterns (urgency, fear, scarcity, ageist tropes,
     novel acronyms without expansion).
3. Read every cited `L-*` entry. You may quote a claim only if the citation
   (DOI + page) is present in the entry's `verification:` block.
4. Draft the body. For the `walkthrough` beat, produce at least two numbered
   steps; each step must declare a prior-step anchor when relevant.
5. Stay within the runtime budget. If you would exceed it, cut content; never
   compress by raising speech rate.

## Output schema

```json
{
  "front_matter": {
    "id": "E-001-ai-is-everywhere",
    "title": "AI is everywhere",
    "target_runtime_seconds": 300,
    "library_refs": ["L-001-knowles-2020"]
  },
  "body_markdown": "# hook\n\nWelcome...\n\n# acknowledge\n\n..."
}
```

`body_markdown` MUST contain exactly eight H1 sections, one per beat, in
canonical order. Return only the JSON object. No prose, no markdown fences.

## Worked example (abbreviated)

```
# hook

A short, warm welcome. One concrete image. No question.

# acknowledge

Name the worry the listener may bring in. Validate, do not dismiss.

# why

The single benefit, in one sentence.
```
