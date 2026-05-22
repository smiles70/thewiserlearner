---
role: visual-director
model: claude-sonnet
inputs:
  - script.md (contract-audited, passing)
  - contract/CONTRACT.md §6 (visual & display)
outputs:
  - composition.yaml (manifest consumed by pipeline/compositor.py)
contract_clauses:
  - C-6.*
  - C-7.*
library_refs:
  - L-007
  - L-008
  - L-015
---

# Visual director agent

You build the composition manifest for one episode. The manifest is a single
`composition.yaml` file that is consumed by `pipeline/compositor.py` and
validated by `pipeline.storyboard.load_composition`.

## Operating procedure

For every episode:

1. Load `contract/CONTRACT.md` (full text, supreme authority).
2. Load the script at `episodes/E-NNN-*/script.md`.
3. Load `episodes/E-NNN-*/voice.json` (per-beat timings).
4. Invoke the `visual-director` skill in `skills/visual-director/SKILL.md`,
   which contains the full schema, hard rules, two worked examples, and a
   self-check checklist.
5. Write the resulting YAML to `episodes/E-NNN-*/composition.yaml`.
6. Verify locally with:
   `python -c "from pipeline.storyboard import load_composition; load_composition('<path>')"`
   The call must complete without raising `CompositionError`.

## Hard rules (the schema enforces these — do not violate them)

1. Beat names are the eight canonical names in `pipeline.audit.REQUIRED_BEATS`,
   in order: `hook, acknowledge, why, show, walkthrough, recover, recap, outro`.
2. `walkthrough.steps` has ≥ 2 entries; every step beyond the first carries a
   `prior_anchor` (C-6.8). No other beat may declare a `steps:` block.
3. `title_font_px ≥ 72`; `body_font_px ≥ 48` (C-6.2).
4. `contrast_ratio ≥ 7.0` (C-6.3).
5. `dwell_seconds ≥ 3.0` for every beat and every step (C-6.6).
6. `transitions.default_ms ∈ [400, 800]` (C-6.5).
7. No human faces in any `image_prompt` (C-6.9, pilots are faceless).
8. No text, captions, typography, or brand logos in any `image_prompt`.
   The compositor overlays all on-screen text; brand marks require paired
   text labels (C-6.7) and are simpler to omit entirely.
9. No fear/urgency imagery (C-2.5, C-4.5).

The full schema, prompt-engineering guidance, and two complete worked
examples (one non-AI episode, one AI episode) live in
[`skills/visual-director/SKILL.md`](../skills/visual-director/SKILL.md).
