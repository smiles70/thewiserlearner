---
name: contract-audit
description: Run the agent-side checks in contract/audit-rubric.md against a script and return JSON.
inputs:
  - script.md
  - contract/CONTRACT.md
  - contract/audit-rubric.md
outputs:
  - agent_checks JSON conforming to the audit-output schema
---

# contract-audit skill

You judge a script against the [agent] checks listed in
`contract/audit-rubric.md`. You return only JSON.

## Process

1. Load and read `contract/CONTRACT.md` in full.
2. Load and read `contract/audit-rubric.md` in full.
3. Read the script.
4. For each [agent] check, decide pass | fail | unsure.
5. Return one JSON object:

```json
{
  "agent_checks": [
    { "id": "A-2.3", "clause": "C-3.4 #1", "status": "pass", "evidence": "...", "line_numbers": [12] }
  ]
}
```

When in doubt, return `unsure`. Never `pass` on a borderline call.
