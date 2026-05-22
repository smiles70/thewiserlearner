---
name: voice-director
description: Author a voice.yaml file (engine, voice, rate, pitch, pauses) for one episode that satisfies contract §5.
inputs:
  - script.md (contract-audited, passing)
  - contract/CONTRACT.md §5 (voice & audio)
outputs:
  - voice.yaml (validated by pipeline.voice_config.load_voice_config)
contract_clauses:
  - "C-5.*"
---

# voice-director skill

You author the voice configuration for one episode. Your output is a single
JSON object that, when serialised to YAML, passes
`pipeline.voice_config.load_voice_config` without modification.

## Process

1. Read `contract/CONTRACT.md` §5 in full. Note clause **C-5.2** (mean speech
   rate 110–120 wpm) and **C-4.11** (no 30 s window above 125 wpm).
2. Read the script's eight beats and count words per beat. Estimate runtime
   using the supplied beat timings from `voice.json` when provided.
3. Choose a voice that is warm, calm, native English, and well-rated for the
   65+ audience. Prefer one of:
   - `en-US-JennyNeural` (default; warmest)
   - `en-US-AriaNeural`
   - `en-GB-SoniaNeural`
   - `en-US-AvaMultilingualNeural`
4. Choose a rate offset in the band **[-30%, +10%]**. Aim for a delivered wpm
   between 112 and 118. Edge TTS Aria default is ~155 wpm, so:
   - target 115 wpm → roughly `-25%` for Aria, `-15%` for Jenny.
5. Keep pitch at `+0Hz` unless the chosen voice sounds shrill (rarely needed).
6. Author the per-beat pause map. After each of `hook`, `acknowledge`, `why`,
   `show`, `recover`, `recap`, `outro` insert a pause of **600–1000 ms**.
   Inside `walkthrough`, insert **800–1200 ms** after each step's last word
   (handled by the TTS module from this map).

## Output schema

```json
{
  "engine": "edge-tts",
  "voice": "en-US-JennyNeural",
  "rate": "-15%",
  "pitch": "+0Hz",
  "pauses": [
    {"after_beat": "hook", "duration_ms": 800},
    {"after_beat": "acknowledge", "duration_ms": 800}
  ],
  "notes": "Brief one-line rationale."
}
```

Return only the JSON object. No prose, no markdown fences.

## Worked example

For a 300 s episode whose script counts 540 words across all beats, target
wpm = 540 × 60 / 300 = 108. Pick `en-US-JennyNeural` at `-10%` for a slightly
brisker but still calm cadence; insert 800 ms pauses after each macro beat.
