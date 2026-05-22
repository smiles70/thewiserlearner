---
name: visual-director
description: Author a composition.yaml manifest for one episode, conforming to the contract's visual clauses (C-6.*) and the storyboard schema validated by pipeline/storyboard.py.
inputs:
  - script.md (contract-audited, passing)
  - voice.json (per-beat timings from pipeline/tts)
  - contract/CONTRACT.md
outputs:
  - composition.yaml (validated by pipeline.storyboard.load_composition)
contract_clauses:
  - C-3.4
  - "C-6.*"
  - "C-7.*"
---

# visual-director skill

You author the composition manifest for one episode. Your output is a single
`composition.yaml` file that passes `pipeline.storyboard.load_composition`
without modification.

## Process

1. Read `contract/CONTRACT.md` §6 and §7 in full.
2. Read the script's eight beats; note the `walkthrough` step count.
3. Read `voice.json` for the per-beat `start_seconds` and `duration_seconds`.
4. For each of the eight beats in canonical order, choose:
   - an **image_prompt**: 1–2 sentences describing a calm, faceless,
     text-free scene that supports the beat's meaning without literalising
     it. The image is background; the message lives in the spoken audio
     and in the overlaid text.
   - **title** (large heading) and optional **subtitle**: short on-screen
     text that anchors the viewer to the beat's idea.
   - **dwell_seconds**: equal to (or slightly less than) the beat's voice
     duration; never less than 3.0; for walkthrough, equal to the beat's
     full voice duration.
5. For the **walkthrough** beat only, populate `steps[]`. One entry per
   numbered step in the script. Each step beyond the first carries a
   `prior_anchor` — the previous step's one-line summary — to satisfy
   C-6.8 (current step + prior anchor visible together).
6. Set `transitions.default_ms` between 400 and 800 (recommended: 600).
7. Set `visual_theme.faceless: true` and `no_text_in_image: true` for
   every pilot.

## Hard rules (the schema rejects violations; do not violate them)

1. **Beat names are fixed.** Use exactly: `hook`, `acknowledge`, `why`,
   `show`, `walkthrough`, `recover`, `recap`, `outro`. In that order. No
   substitutions, no insertions.
2. **Walkthrough has ≥ 2 steps.** No other beat may have a `steps:` block.
3. **`title_font_px ≥ 72`**, **`body_font_px ≥ 48`** (C-6.2).
4. **`contrast_ratio ≥ 7.0`** (C-6.3). Compute against your declared
   palette; do not estimate.
5. **`dwell_seconds ≥ 3.0`** for every beat and every step (C-6.6).
6. **`transitions.default_ms ∈ [400, 800]`** (C-6.5).
7. **No human faces** in any `image_prompt` (C-6.9, pilots are faceless).
8. **No text, captions, or typography** inside any `image_prompt`. The
   compositor overlays all on-screen text. If the image has its own
   text, the result violates C-6.7 (icons/labels) and the contract.
9. **No brand logos** in any `image_prompt` (C-6.7 mandates paired text
   labels for any brand mark; safer to skip them entirely).
10. **No fear/urgency imagery** — no clocks racing, no warning signs, no
    "left behind" visual metaphors (C-2.5, C-4.5).

## Tone for image prompts

The viewer is a competent older adult in a calm domestic setting. Aim for:

- Soft natural light, late-morning or early-afternoon.
- Familiar domestic objects: notebooks, tea, kitchens, hands resting on
  surfaces, open windows, plain tables.
- Quiet compositions; one or two subjects per frame; generous negative space.
- Muted, warm-neutral palettes; high contrast against overlaid white text.

Avoid:

- Office/corporate stock imagery.
- Futuristic/cyberpunk/sci-fi tropes.
- Crowds, motion blur, dramatic lighting, lens flares.
- Cute or whimsical characters.

## Output format

Return **only** the YAML body of the manifest, no prose, no markdown fences.
The first character of your reply is `f` (the start of `format:`).

---

## Worked example 1 — non-AI episode (E-001 "AI Is Everywhere Now")

This is the canonical reference. The four-step walkthrough demonstrates the
prior-anchor pattern.

```yaml
format: 1920x1080
fps: 25
visual_theme:
  palette: warm-neutral-morning-light
  mood: calm, dignified, quiet
  faceless: true
  no_text_in_image: true
transitions:
  default_ms: 600
  min_ms: 400
  max_ms: 800
beats:
  - beat: hook
    image_prompt: "A softly-lit kitchen table at mid-morning, a phone resting on it showing a weather pane. Warm window light from the side, plain white mug nearby. Natural shadow, generous negative space, no people."
    title: "AI Is Everywhere Now"
    subtitle: "A calm map of where it already lives."
    title_font_px: 88
    body_font_px: 56
    contrast_ratio: 16.9
    dwell_seconds: 40.0
  - beat: acknowledge
    image_prompt: "A small open notebook beside a cup of tea on a wooden surface. Soft daylight, a single pencil, pages slightly worn. Quiet, unhurried."
    title: "The names sound similar."
    subtitle: "That is the point of this map."
    title_font_px: 80
    body_font_px: 52
    contrast_ratio: 15.0
    dwell_seconds: 39.0
  - beat: why
    image_prompt: "A folded paper map laid flat on a kitchen table, edges curled, light from a window. No labels visible. Warm neutral tones."
    title: "The choice is yours."
    title_font_px: 80
    body_font_px: 52
    contrast_ratio: 15.0
    dwell_seconds: 24.0
  - beat: show
    image_prompt: "A phone face-up on a wooden counter showing a soft blurred app pane, indistinct. Coffee mug to the side. Calm domestic setting."
    title: "One minute of your day."
    title_font_px: 80
    body_font_px: 52
    contrast_ratio: 15.0
    dwell_seconds: 33.0
  - beat: walkthrough
    image_prompt: "Four small everyday objects arranged on a wooden table: a small speaker, a phone, a camera, and a closed envelope. Even soft light from above, plenty of space between them, top-down composition."
    title: "Four places AI lives."
    title_font_px: 80
    body_font_px: 52
    contrast_ratio: 15.0
    dwell_seconds: 80.0
    steps:
      - index: 1
        text: "Part one. The voice assistants."
        dwell_seconds: 18.0
      - index: 2
        text: "Part two. The chat assistants."
        prior_anchor: "1. Voice assistants — Siri, Alexa, Google."
        dwell_seconds: 22.0
      - index: 3
        text: "Part three. The picture and photo helpers."
        prior_anchor: "2. Chat assistants — ChatGPT, Claude, Gemini."
        dwell_seconds: 18.0
      - index: 4
        text: "Part four. The AI inside the apps you already use."
        prior_anchor: "3. Picture and photo helpers."
        dwell_seconds: 18.0
  - beat: recover
    image_prompt: "A single steaming cup of tea on a quiet counter, late-morning light, hands not visible. Calm, restful framing."
    title: "Pick one. The rest can wait."
    title_font_px: 80
    body_font_px: 52
    contrast_ratio: 15.0
    dwell_seconds: 27.0
  - beat: recap
    image_prompt: "A simple printed map on a table with four small numbered markers, gentle daylight. No legend visible."
    title: "Voice. Chat. Pictures. Apps."
    title_font_px: 80
    body_font_px: 52
    contrast_ratio: 15.0
    dwell_seconds: 23.0
  - beat: outro
    image_prompt: "An open notebook beside a closed pen on a wooden surface, soft daylight, plain background, no text on the page."
    title: "Thank you for being here."
    title_font_px: 80
    body_font_px: 52
    contrast_ratio: 15.0
    dwell_seconds: 17.0
```

## Worked example 2 — AI episode (drafting a short note with Claude)

Shows the pattern when the topic *is* the AI tool. Note that imagery never
shows a Claude logo or interface — the visual register stays domestic; the
substance lives in the spoken audio and overlaid text.

```yaml
format: 1920x1080
fps: 25
visual_theme:
  palette: warm-neutral-evening-lamp
  mood: calm, deliberate, considered
  faceless: true
  no_text_in_image: true
transitions:
  default_ms: 600
  min_ms: 400
  max_ms: 800
beats:
  - beat: hook
    image_prompt: "A small writing desk with a single lamp turned on, an open notebook and a phone face-down beside it. Warm evening light, no people, plenty of space."
    title: "Drafting a note in five minutes."
    title_font_px: 88
    body_font_px: 56
    contrast_ratio: 16.5
    dwell_seconds: 22.0
  - beat: acknowledge
    image_prompt: "A blank sheet of paper with a pen resting across it, soft warm light, no writing visible."
    title: "It will sound like you."
    title_font_px: 80
    body_font_px: 52
    contrast_ratio: 15.0
    dwell_seconds: 20.0
  - beat: why
    image_prompt: "A handwritten envelope on a kitchen table beside a mug, late-afternoon light, no addresses visible."
    title: "Your voice, in the message."
    title_font_px: 80
    body_font_px: 52
    contrast_ratio: 15.0
    dwell_seconds: 18.0
  - beat: show
    image_prompt: "A phone face-up on a wooden surface showing a soft blurred chat pane, no readable text. Warm side light."
    title: "One sentence in. One draft out."
    title_font_px: 80
    body_font_px: 52
    contrast_ratio: 15.0
    dwell_seconds: 28.0
  - beat: walkthrough
    image_prompt: "Four numbered tiles laid out on a wooden table, plain wood grain, even soft light from above. Tiles are blank. Top-down view, generous spacing."
    title: "Four small steps."
    title_font_px: 80
    body_font_px: 52
    contrast_ratio: 15.0
    dwell_seconds: 70.0
    steps:
      - index: 1
        text: "Step one. Open the Claude app on your phone."
        dwell_seconds: 16.0
      - index: 2
        text: "Step two. Type one sentence about what you want to say."
        prior_anchor: "1. Open Claude on your phone."
        dwell_seconds: 18.0
      - index: 3
        text: "Step three. Read the draft, then ask Claude to adjust the tone."
        prior_anchor: "2. Type one sentence."
        dwell_seconds: 18.0
      - index: 4
        text: "Step four. Copy the result into your messages app."
        prior_anchor: "3. Read and adjust the tone."
        dwell_seconds: 18.0
  - beat: recover
    image_prompt: "An open notebook with a pen resting in the gutter, evening light, no writing visible."
    title: "If it misses, nudge it. Keep going."
    title_font_px: 80
    body_font_px: 52
    contrast_ratio: 15.0
    dwell_seconds: 24.0
  - beat: recap
    image_prompt: "A folded handwritten note on a wooden surface beside a teacup, calm warm light."
    title: "You have just drafted a note with Claude."
    title_font_px: 80
    body_font_px: 52
    contrast_ratio: 15.0
    dwell_seconds: 18.0
  - beat: outro
    image_prompt: "A closed notebook and a pen at rest on a wooden desk, soft lamp light, plain background."
    title: "Next: editing the tone, in detail."
    title_font_px: 80
    body_font_px: 52
    contrast_ratio: 15.0
    dwell_seconds: 16.0
```

## Self-check before returning

Before you return your YAML, verify each item:

- [ ] All eight beat names appear in canonical order.
- [ ] `walkthrough.steps` has ≥ 2 entries; every step beyond the first
      carries a `prior_anchor`.
- [ ] No other beat has a `steps:` block.
- [ ] Every `title_font_px ≥ 72`, every `body_font_px ≥ 48`.
- [ ] Every `contrast_ratio ≥ 7.0`.
- [ ] Every `dwell_seconds ≥ 3.0`.
- [ ] `transitions.default_ms` is between 400 and 800.
- [ ] No `image_prompt` mentions faces, people, text, captions, or brand logos.
- [ ] `visual_theme.faceless: true` and `visual_theme.no_text_in_image: true`.

If any check fails, fix it before returning. The schema validator will
reject the manifest otherwise and your output will be discarded.
