---
role: publisher
model: deterministic
inputs:
  - episode.mp4
  - thumbnail.png
  - seo.yaml
outputs:
  - publish-receipt.json (video_id, url, status)
contract_clauses:
  - C-9.*
library_refs: []
---

# Publisher agent

Deterministic. Drives `pipeline/youtube.py` to upload, set metadata, attach
thumbnail, and add the video to the channel playlist. Never publishes a video
whose `audit.json` verdict is not `pass`. Never publishes without a
`seo.yaml` that satisfies contract clauses C-9.*.
