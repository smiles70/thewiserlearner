---
title: Visual Pipeline Blueprint (v0.2)
status: approved, not yet implemented
owner: pipeline
---

# Visual Pipeline Blueprint (v0.2)

Persistent record of the v0.2 visuals architecture so we can pick it up across
sessions without re-deciding.

## Decision: generator = fal.ai

Selected over Replicate / Google Veo / Pollinations on three criteria the
user named: free to start, low learning curve, fast API integration.

- Free credits on signup, no card.
- Single REST + official Python client (`fal-client`); ~5 lines to call.
- Aggregator: 1,000+ models. Switching from cheap stills (`fal-ai/flux/schnell`)
  to motion (`fal-ai/kling-video/v2`, `fal-ai/veo3`) is a config string change.
- 30–50% cheaper than Replicate at scale.
- No code lock-in: provider interface is abstract; we can swap providers.

Cost envelope: ~$0.003/image × 8 beats ≈ $0.024/episode for still cards.
Motion clips run higher (~$0.05–$0.30/clip depending on model) — gated by
`FAL_MAX_USD_PER_EPISODE` env (default $0.50).

## Architecture (4 layers)

```
Layer 1 — Claude skills (storyboarding intelligence)
  .claude/skills/visual-director/    (adapted from aicontentskills/ai-video-storyboard-skill)
  .claude/skills/storyboard-artist/  (adapted from RainLib/AI-Storyboard)
  .claude/skills/storyboard-review/  (wraps pipeline.audit as the Director gate)

Layer 2 — Storyboard data on disk
  episodes/E-XXX/storyboard.yaml             (visual theme + 8 shot specs)
  episodes/E-XXX/visuals/beat-{N}.png|.mp4   (generated per beat)
  episodes/E-XXX/visuals/manifest.json       (provider, model, seed, cost, prompt)

Layer 3 — Python pipeline modules
  pipeline/storyboard.py            (parse + contract-validate storyboard.yaml)
  pipeline/visuals.py               (abstract Generator interface)
  pipeline/providers/fal.py         (fal.ai concrete impl)
  pipeline/providers/local.py       (Pillow fallback = current v0.1 cards)
  pipeline/compositor.py            (UPGRADED to consume per-beat imagery)

Layer 4 — CLI
  pipeline storyboard <script.md>   NEW
  pipeline visuals    <script.md>   NEW
  pipeline composite  <script.md>   UPGRADED
  pipeline run        <script.md>   extended chain
```

## End-to-end flow

`script.md → audit (gate) → storyboard skill → storyboard-review (gate) →
storyboard.yaml → visuals (fal.ai or local) → visuals/beat-{N}.png +
manifest.json → tts → captions → compositor (per-beat + Ken Burns) →
episode.mp4`

`voice.json` remains the **single source of truth for timing**. Storyboard
durations are derived from voice.json beats, not vice versa.

## Contract integration points

- C-6.1 1920×1080 16:9 — `visuals.normalize()` enforces on every image
- C-6.5 no rapid motion — storyboard schema forbids `motion_intensity > "slow"`
- C-6.3 ≥7:1 contrast — compositor renders overlays on a darkened gradient
  band; verified by `audit.check_overlay_contrast()`
- C-9.* AI disclosure — `manifest.json` records `ai_generated: true`; meta
  template auto-appends disclosure to YouTube description
- Library/no-placeholder rule — storyboard prompts cannot cite unverified
  claims; storyboard-review gates

The Director role in the Claude skill graph **delegates PASS/FAIL to
`pipeline.audit`** so we keep one source of truth.

## 720° regression rules (must-hold invariants)

1. With no `FAL_KEY`, pipeline runs identically to today using `local` provider.
2. Existing tests stay green without modification.
3. `pipeline run` works on E-001/2/3 with one extra stage inserted.
4. `voice.json` timings are authoritative for all downstream stages.
5. Manifest records every API call (prompt, model, seed, cost, hash) for reproducibility.
6. Resume support: `pipeline run --from-stage visuals` skips completed beats.
7. Cost cap aborts visuals stage cleanly, preserving audited script/voice/captions.
8. Provider refusal (NSFW/policy) retries N=2 then falls back to local for that beat only.

## Failure-mode matrix

| Failure                           | Action                                              |
|-----------------------------------|-----------------------------------------------------|
| `FAL_KEY` not set                 | Fall back to local provider; no error              |
| fal.ai 5xx / rate-limit           | tenacity exponential backoff x3 → local fallback   |
| Cost cap exceeded                 | Abort visuals stage; keep prior artifacts          |
| Safety refusal from provider      | Re-prompt N=2 with softer phrasing → local card    |
| Generated image fails C-6.* audit | Re-render or fall back to local card for that beat |
| Model deprecated                  | Manifest pins model version; nightly smoke test    |

## Execution sequence (deterministic)

1. Vendor the two source skills into `.claude/skills/`; adapt theme defaults
   to geragogy contract palette.
2. Define `contract/storyboard.schema.json` (machine-validatable).
3. Build `pipeline/visuals.py` with abstract `Generator` + `local` provider
   only. Ship and test fully offline.
4. Upgrade `pipeline/compositor.py` for per-beat images + Ken Burns. Keep
   fallback path to v0.1 title card intact.
5. Re-render E-001 with local provider only — proves the new compositor works
   before any API integration.
6. Build `pipeline/providers/fal.py` behind the same interface. Marked
   `pragma: no cover - network`.
7. Run E-001 with `FAL_KEY` set → real AI visuals.
8. Wire `storyboard-artist` + `storyboard-review` Claude skills so future
   episodes produce `storyboard.yaml` automatically.

Steps 1–5 are fully offline and risk-free.
Step 6 needs the user to sign up at fal.ai (~2 min, free credits).
Step 8 closes the loop for automation on E-004+.

## Pending user actions

- [ ] Sign up at https://fal.ai → copy API key → paste into `.env` as `FAL_KEY`
- [ ] Approve default image model: `fal-ai/flux/schnell` (cheap, fast, free-credit-friendly)
- [ ] Decide on motion model for v0.3 (candidates: `fal-ai/kling-video/v2`, `fal-ai/veo3`, `fal-ai/runway-gen3`)
