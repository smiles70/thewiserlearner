# Architecture

This document is the canonical reference for **Part 1 — the 720° Pipeline Blueprint**.
It describes the fully automated production system end-to-end. Future parts (the
Library, the Contract, the pilot scripts, the runnable pipeline) build on what is
declared here.

## Prime directives

1. The Contract is supreme. Any pipeline choice is a candidate until the Geragogy
   Contract ratifies it against the evidence library.
2. Empathetic, never apologetic. Never condescending.
3. The learner is somebody's beloved Naani.
4. No claim without a citation.
5. No placeholders in the library.

## One-time manual onboarding (~5 minutes)

| # | Step | Where |
|---|---|---|
| 1 | Create a dedicated Google account: `thewiserlearner@gmail.com` | accounts.google.com |
| 2 | Create a YouTube channel named **The Wiser Learner** | youtube.com |
| 3 | Claim handle **@thewiserlearner** | youtube.com/handle |
| 4 | Create Porkbun account | porkbun.com |
| 5 | Add payment method to Porkbun (one card, used once) | porkbun.com/account/billing |

Everything below this line runs without human input.

## High-level architecture

```text
Topic intake
  -> Research (OpenAlex, Crossref, Unpaywall, ERIC, PubMed)
  -> Outline
  -> Script draft (<=480 words)
  -> Contract audit (hard gate)
  -> TTS synthesis (Edge TTS / Kokoro / Piper)
  -> Caption generation (Whisper)
  -> B-roll shotlist
  -> B-roll fetch (Pexels, Pixabay, Coverr)
  -> Video assembly (FFmpeg)
  -> Thumbnail render (Pillow)
  -> SEO metadata
  -> Upload + schedule (YouTube Data API v3)
  -> Analytics ingest (YouTube Analytics API)
  -> Weekly contract evolution review
```

## The 14 stages

See `docs/architecture.md` Part 1 in the project chat history for the full table.
The condensed version:

| Stage | Output | APIs / tools |
|---|---|---|
| 1. Topic intake | `episodes/{slug}/brief.md` | — |
| 2. Research | `episodes/{slug}/evidence.json` | OpenAlex, Crossref, Unpaywall, ERIC, PubMed |
| 3. Outline | `outline.md` | Claude |
| 4. Script draft | `script.draft.md` | Claude |
| 5. Contract audit | PASS / FAIL | Deterministic + LLM-as-judge |
| 6. TTS | `voice.wav` | Edge TTS (Kokoro fallback) |
| 7. Captions | `captions.srt` | faster-whisper |
| 8. Shotlist | `shotlist.json` | Claude |
| 9. B-roll fetch | `broll/*.mp4` | Pexels, Pixabay, Coverr |
| 10. Video assembly | `final.mp4` | FFmpeg |
| 11. Thumbnail | `thumb.png` | Pillow |
| 12. SEO metadata | `meta.json` | Claude |
| 13. Upload | YouTube video | YouTube Data API v3 |
| 14. Analytics | `analytics/perf.sqlite` | YouTube Analytics API |

## Runtime

GitHub Actions. See [`adr/0001-runtime-github-actions.md`](./adr/0001-runtime-github-actions.md).

## Repository layout

| Path | Purpose |
|---|---|
| `library/` | Verified geragogy sources (Part 2) |
| `contract/` | The Geragogy Contract (Part 3) |
| `skills/` | Claude Skills bundles (Part 5) |
| `.claude/agents/` | Claude Code sub-agents (Part 5) |
| `mcp/` | Custom MCP servers (Part 5) |
| `pipeline/` | 14 stage scripts (Part 5) |
| `episodes/` | Per-episode build dirs |
| `analytics/` | SQLite DB |
| `docs/` | This file + ADRs |
| `tests/` | Test suite |

## Cost ledger

| Item | Monthly cost |
|---|---|
| GitHub Actions (public repo) | $0 |
| Anthropic API (free tier → Haiku) | $0 – $3 |
| OpenAlex / Crossref / Unpaywall / ERIC / PubMed | $0 |
| Pexels / Pixabay / Coverr | $0 |
| Edge TTS | $0 |
| Whisper / FFmpeg / Pillow | $0 |
| YouTube Data + Analytics APIs | $0 |
| Atkinson Hyperlegible font | $0 |
| YouTube Audio Library / Pixabay Music | $0 |
| `thewiserlearner.com` domain (Porkbun) | ~$1 |
| `mynaani.com` (already owned) | — |
| **Total** | **~$1** |
