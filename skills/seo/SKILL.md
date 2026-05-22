---
name: seo
description: Author a contract-compliant YouTube title, description, tags, and chapter list for one episode.
inputs:
  - script.md (contract-audited, passing)
  - contract/CONTRACT.md §2, §4, §9
outputs:
  - seo.yaml (matches pipeline.seo_meta.SeoMeta)
contract_clauses:
  - "C-2.*"
  - "C-4.*"
  - "C-9.*"
---

# seo skill

You author the YouTube-bound metadata for one episode. Your output is a JSON
object that, when serialised to YAML, passes
`pipeline.seo_meta.load_seo_meta` without modification.

## Process

1. Read the script.
2. Read contract sections §2 (editorial posture) and §4 (forbidden patterns).
3. Author the **title** (≤ 70 characters):
   - No urgency, fear, or scarcity vocabulary.
   - No clickbait punctuation (`!`, `?!`, ellipses).
   - Plain words, sentence case.
4. Author the **description** (40–4500 characters):
   - First sentence is a one-line summary suitable for the YouTube preview card.
   - Then a short paragraph on what the episode covers.
   - Then a `Chapters:` section listing the chapter starts in HH:MM:SS form.
   - Then a `Sources:` section listing the cited L-entries by L-code and title.
5. Author **tags** (max 30, ≤ 30 chars each, no commas inside a tag).
6. Author **chapters**: first chapter MUST start at 0.0 seconds. Starts must
   be strictly increasing. Titles 3–80 characters.
7. Set **visibility** to `unlisted` for pilots, `public` for shipped episodes.

## Output schema

```json
{
  "title": "AI is everywhere - what older adults should know",
  "description": "A calm four-minute introduction...\n\nChapters:\n00:00 Intro\n...",
  "tags": ["ai for seniors", "geragogy"],
  "chapters": [
    {"start_seconds": 0.0, "title": "Introduction"}
  ],
  "visibility": "public"
}
```

Return only the JSON object. No prose, no markdown fences.
