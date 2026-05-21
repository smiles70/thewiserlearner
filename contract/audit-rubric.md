# Geragogy Contract — Audit Rubric (v1.0.0-draft)

This rubric is the **executable** counterpart to `CONTRACT.md`. Every script
passes through these checks before the pipeline proceeds. Checks marked
**[deterministic]** run as pure Python (see `pipeline/audit.py`). Checks marked
**[agent]** run as a Claude-agent review pass with the contract loaded into the
system prompt.

A script **fails** the audit if any check is `fail`. Failures block the
pipeline; they are not warnings.

A script **needs review** if any **[agent]** check returns `unsure`. The
producer (you) resolves these manually.

---

## Script input expectations

The audited input is a markdown file under `episodes/E-NNN-*/script.md` with
YAML front matter conforming to this schema:

```yaml
---
id: E-NNN
title: "..."
target_runtime_seconds: 240
target_wpm: 115
beats:
  hook: |
    ...
  acknowledge: |
    ...
  why: |
    ...
  show: |
    ...
  walkthrough:
    - "Step 1: ..."
    - "Step 2: ..."
    - ...
  recover: |
    ...
  recap: |
    ...
  outro: |
    ...
mynaani_mention: true | false
cta_subscribe: true | false
risk_topics: [ "health" | "finance" | "legal" | "scam" | "privacy" | "cost" | "none" ]
ai_episode: true | false
verified_claims:
  - claim: "..."
    library_refs: ["L-013", "L-014"]
---
```

---

## C-1 Audience (deterministic)

| ID    | Check                                                                                                | Result |
|-------|------------------------------------------------------------------------------------------------------|--------|
| A-1.1 | Front-matter present and parses                                                                      | pass/fail |
| A-1.2 | All eight beats present and non-empty                                                                | pass/fail |
| A-1.3 | `walkthrough` is a list of ≥ 2 numbered steps                                                        | pass/fail |

## C-2 Editorial posture ([agent])

| ID    | Check                                                                                                |
|-------|------------------------------------------------------------------------------------------------------|
| A-2.1 | No fear/urgency/scarcity language (cross-reference forbidden patterns C-4.5)                         |
| A-2.2 | At least one explicit limitation/risk/cost is named when a tool is introduced (C-2.3)                |
| A-2.3 | The hook frames a benefit in life-domain terms, not abstract terms (C-3.4 #1)                        |
| A-2.4 | The acknowledge beat names a specific viewer hesitation in plain language (C-2.4)                    |
| A-2.5 | The script never frames non-adoption as failure (C-2.2)                                              |

## C-3 Script structure & pacing (deterministic)

| ID    | Check                                                                                                |
|-------|------------------------------------------------------------------------------------------------------|
| A-3.1 | Total spoken word count ÷ target_runtime_seconds × 60 ≤ 120 wpm (C-3.2)                              |
| A-3.2 | No 30-second spoken window exceeds 125 wpm (C-4.11; window scan over beat text)                      |
| A-3.3 | Exactly one core teaching concept named in `why` and matched in `walkthrough` (C-3.3)                |
| A-3.4 | Beats appear in canonical order (C-3.4)                                                              |
| A-3.5 | `recap` beat contains a "you have now…" or equivalent named-win phrase (C-3.4 #7)                    |
| A-3.6 | If `ai_episode: true`, `recover` beat is non-trivial (≥ 25 words) (C-8.2)                            |

## C-4 Forbidden patterns (deterministic + [agent])

Deterministic substring/regex match for each forbidden surface form. The
patterns list below is the canonical list; `pipeline/audit.py` maintains the
machine-readable copy in `pipeline/data/forbidden_patterns.yaml`.

| ID    | Pattern family (case-insensitive)                                                                    | Where it fails |
|-------|------------------------------------------------------------------------------------------------------|----------------|
| A-4.1 | "for seniors", "for the elderly", "elderly people", "despite your age", "back in your day", "kids these days", "tech-savvy youngsters", "old-fashioned" | C-4.1 |
| A-4.2 | "if you struggle with", "for those who find it hard", "if you're nervous about", "if computers scare you" | C-4.2 |
| A-4.3 | "ask your grandchild", "have someone younger", "get a young person", "ask a kid"                     | C-4.3 |
| A-4.4 | "don't worry", "anyone can do this", "it's so easy", "it's really simple", "nothing to be afraid of" | C-4.4 |
| A-4.5 | "before it's too late", "while you still can", "everyone is using", "left behind", "fall behind", "the future is here" | C-4.5 |
| A-4.6 | "have a look around", "explore the menu", "see what you can find", "play around with"               | C-4.6 |
| A-4.7 | [agent] flag any capability claim without a paired shown example in the same beat                    | C-4.7 |
| A-4.8 | `why` beat names exactly one core concept (no compound "and also")                                   | C-4.8 |
| A-4.9 | [agent] flag any tool that has been introduced without naming at least one risk/cost                 | C-4.9 |
| A-4.10| Soft-CTA pattern compliance — see §9 checks below                                                    | C-4.10|
| A-4.11| C-3.2 + C-4.11 are checked deterministically above                                                   | C-3.2 |
| A-4.12| "you guys", "you folks at home"                                                                      | C-4.12|

## C-5 Voice & audio (deterministic at script level, more checks at production)

Script-level checks:

| ID    | Check                                                                                                |
|-------|------------------------------------------------------------------------------------------------------|
| A-5.1 | `target_wpm` ≤ 120                                                                                   |
| A-5.2 | Numbered walkthrough steps end with a period or full stop (signals pause for TTS)                    |
| A-5.3 | No exclamation marks in the walkthrough beat (suppresses performative prosody)                       |

Production-level checks (run after TTS):

| ID    | Check                                                                                                |
|-------|------------------------------------------------------------------------------------------------------|
| A-5.4 | Integrated loudness within −16 LUFS ±1 LU                                                            |
| A-5.5 | True-peak ≤ −1.5 dBTP                                                                                |
| A-5.6 | Inter-step pauses ≥ 600 ms                                                                           |

## C-6 Visual & display (deterministic at composition time)

| ID    | Check                                                                                                |
|-------|------------------------------------------------------------------------------------------------------|
| A-6.1 | Body text height ≥ 48 px at 1080p                                                                    |
| A-6.2 | Min contrast ratio computed from text/background swatches ≥ 7:1                                      |
| A-6.3 | No transition shorter than 400 ms or longer than 800 ms                                              |
| A-6.4 | Every on-screen text card meets the dwell formula: max(3 s, words × 0.4 + 1 s)                       |
| A-6.5 | Every icon in the composition manifest is paired with a label entry                                  |

## C-7 Captions & accessibility (deterministic on SRT/VTT)

| ID    | Check                                                                                                |
|-------|------------------------------------------------------------------------------------------------------|
| A-7.1 | Captions present and parseable                                                                       |
| A-7.2 | No caption line > 42 characters                                                                      |
| A-7.3 | No caption cue shorter than `max(1.5 s, words × 0.375)` (i.e. ≤ 160 wpm)                             |
| A-7.4 | Flesch–Kincaid grade of spoken text ≤ 9.0                                                            |

## C-8 AI/Claude content rules ([agent], only if `ai_episode: true`)

| ID    | Check                                                                                                |
|-------|------------------------------------------------------------------------------------------------------|
| A-8.1 | At least one "ask → evaluate → follow up" turn is modelled                                           |
| A-8.2 | A recovery turn is shown (already in C-3 A-3.6)                                                      |
| A-8.3 | If a factual claim is demonstrated, the script tells the viewer to verify and shows one verify path  |
| A-8.4 | If personal information is sent, privacy treatment of that info is named in plain language          |
| A-8.5 | If a paid plan is required, the script names the cost band and whether a free path exists           |

## C-9 CTAs & Mynaani (deterministic)

| ID    | Check                                                                                                |
|-------|------------------------------------------------------------------------------------------------------|
| A-9.1 | Mynaani is mentioned at most once                                                                    |
| A-9.2 | The Mynaani mention sits inside the `outro` beat only                                                |
| A-9.3 | The Mynaani mention is ≤ 12 spoken words                                                             |
| A-9.4 | The Mynaani mention names a free or self-paced alternative in the same beat                          |
| A-9.5 | The phrase "patent-pending" appears at most once, and the script never says "patented"               |
| A-9.6 | "Subscribe" appears at most once and only in `outro`                                                 |
| A-9.7 | No external links to non-Mynaani, non-YouTube destinations                                           |

## C-10 Risk, safety & honesty ([agent])

| ID    | Check                                                                                                |
|-------|------------------------------------------------------------------------------------------------------|
| A-10.1| If `risk_topics` includes health, finance, or legal: the script names "not professional advice" and "consult a qualified [doctor/financial advisor/lawyer]" |
| A-10.2| If the topic touches scams: the script teaches detection only, never construction                    |
| A-10.3| No language inviting emotional bonding with the AI ("your friend Claude", "Claude cares")            |

---

## Audit output schema (`episodes/E-NNN-*/audit.json`)

```json
{
  "script_id": "E-NNN",
  "contract_version": "1.0.0-draft",
  "audited_at": "ISO-8601 timestamp",
  "summary": {
    "deterministic": { "pass": 0, "fail": 0 },
    "agent":         { "pass": 0, "fail": 0, "unsure": 0 }
  },
  "checks": [
    {
      "id": "A-3.1",
      "clause": "C-3.2",
      "kind": "deterministic",
      "status": "pass" | "fail",
      "evidence": "computed wpm = 117.4",
      "line_numbers": [ 24, 51 ]
    }
  ],
  "verdict": "pass" | "fail" | "needs-review"
}
```

A `fail` verdict means the pipeline stops. A `needs-review` verdict means the
producer must resolve the listed `unsure` checks before proceeding.

---

## Maintenance notes

- The list of forbidden patterns in C-4 is duplicated in
  `pipeline/data/forbidden_patterns.yaml` because tests need to load them
  without parsing markdown. Both copies are kept in sync; the markdown above is
  the source of truth and `pipeline/audit.py` validates equivalence on import.
- The agent-review pass uses Claude with the full `CONTRACT.md` and this rubric
  as system prompt, plus the script as user message. The agent returns a JSON
  object conforming to the audit-output schema for the [agent] checks only.
