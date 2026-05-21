---
role: compositor
model: deterministic  # this role is mostly code, with an agent fallback for ambiguity
inputs:
  - voice.wav + voice.json (from voice-director / tts)
  - captions.srt (from captioner)
  - composition.yaml (from visual-director)
outputs:
  - episode.mp4
contract_clauses:
  - C-5.*
  - C-6.*
  - C-7.*
library_refs:
  - L-007
  - L-008
---

# Compositor agent

Mostly deterministic: invokes `pipeline/compositor.py` against the manifest.
An agent pass is consulted only when the manifest violates contract specs
and human-readable diagnostics are needed (e.g. "step 3 dwell is 2.6 s but
needs ≥ 3.0 s; suggest moving the b-roll cue earlier by 0.4 s").
