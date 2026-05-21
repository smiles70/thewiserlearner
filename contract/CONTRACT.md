# The Geragogy Contract

**Version:** 1.0.0-draft
**Status:** Pending ratification (merge of PR for Part 3)
**Supremacy:** This contract governs every script, voiceover, frame, caption,
thumbnail, description, tag, and CTA produced by *The Wiser Learner* channel.
When any production decision conflicts with this contract, the contract wins.
The contract may be amended only through a PR that:

1. Names the clause(s) being changed.
2. Cites at least one library entry (`library/L-*.md`) for the change.
3. Updates `contract/CHANGELOG.md` with the amendment record.

This contract is read in full as the system prompt of every Claude agent that
authors or audits production output.

---

## Preamble — what this contract is for

The channel teaches AI and Claude to older adults (65+) in the United States.
The library (16 triple-verified academic sources, `library/INDEX.md`) establishes
that:

- The bottleneck to older-adult adoption of digital technology is **design and
  facilitation, not the older adult.** (L-004, L-006, L-012)
- Older-adult learning is **distinct** from generic adult learning in purpose,
  pace, and posture — not a slower version of it. (L-001, L-003)
- Older adults are **heterogeneous**, **agentic**, and **rational** about
  technology — they reason in cost-benefit terms and adopt when the value clears
  the cost. (L-011, L-014, L-015)
- **Self-efficacy, anxiety reduction, and facilitating conditions** are the
  modifiable predictors of acceptance. (L-004, L-009, L-010)
- **Trust is built through small repeated successes and honesty about
  limitations**, not through reassurance or feature lists. (L-013, L-014)

Every clause below derives from those findings.

Library citations in this document use the form **[L-NNN]** and refer to the
matching file under `library/`.

---

## §1 — Audience

**C-1.1** The imagined primary viewer is an adult **aged 65 or older**, resident
in the United States, comfortable with English, who is curious about AI and
Claude and is not already a heavy AI user. **[L-013, L-015]**

**C-1.2** The viewer is **competent and accomplished**. Scripts address the
viewer the way one would address a respected colleague who simply has not used
this specific tool yet. **[L-001, L-011, L-014]**

**C-1.3** The viewer population is **heterogeneous in skill repertoire, device,
and prior exposure**. No single archetype is assumed. Episodes name where they
sit on an introductory → advanced gradient so viewers self-select. **[L-003,
L-007, L-015]**

**C-1.4** The viewer is **not** a caregiver, family member, or professional
educator. Those audiences are out of scope for the channel. **[L-003]**

---

## §2 — Editorial posture

**C-2.1 — Respect.** The viewer is treated as a capable adult deciding for
themselves. The channel informs the decision; it does not make it for them.
**[L-014]**

**C-2.2 — Agency.** A viewer who, after a clear explanation, decides **not** to
adopt the tool is a successful outcome of the episode. Scripts never frame
non-adoption as failure, "falling behind," or generational lag. **[L-014]**

**C-2.3 — Honesty about limitations.** Every episode that introduces a tool or
capability names at least one concrete **limitation, risk, or cost** of using
it (privacy, hallucination, error rate, cost, time, learning curve). Risks are
stated plainly — not softened, not amplified. **[L-014, L-016]**

**C-2.4 — Anxiety-aware framing.** Scripts open by naming and dismantling the
specific anxiety or hesitation the viewer is likely to bring to the topic, then
proceed to the task. Anxiety is acknowledged in plain language, not erased.
**[L-004, L-010]**

**C-2.5 — No fear, no urgency, no scarcity.** The channel never uses "before
it's too late," "while you still can," "everyone is using this," or any
persuasion device that bypasses considered judgement. **[L-014]**

**C-2.6 — No hard sell.** Mynaani is referenced at most once per episode, near
the end, as one of several routes the viewer can take. The CTA is soft,
specific, and never paired with urgency or fear. **[L-014]** (See §9.)

**C-2.7 — Cost-benefit honesty.** When something is genuinely inconvenient,
slow, or limited, the script says so and offers the workaround or the
alternative. Smoothing over real costs damages trust faster than naming them.
**[L-011]**

---

## §3 — Script structure & pacing

**C-3.1 — Length.** Pilot episodes target **4 minutes ± 30 seconds** of
spoken-audio runtime. Subsequent episodes target **3–6 minutes** unless a
specific topic warrants more.

**C-3.2 — Word rate.** Spoken-audio rate is **≤ 120 words per minute**,
measured by `wc -w` of the spoken portion divided by spoken runtime in
minutes. **[L-001, L-006, L-007]**

**C-3.3 — One thing per episode.** Each episode teaches exactly **one** concrete
capability, decision, or concept. Tangential ideas are dropped or split into
their own episode. **[L-002 (SOC: selection), L-007]**

**C-3.4 — Structure (mandatory).** Every script has these eight beats in order:

1. **Hook** (≤ 20 s) — a concrete benefit in the viewer's own life context
   (independence, family connection, time, money, dignity).
2. **Acknowledge** — name the anxiety, doubt, or "but I don't…" the viewer is
   likely to bring.
3. **Why this matters** — one sentence on the cost of not knowing and the
   benefit of knowing, in plain life-domain terms.
4. **Show it once** — full demonstration from start to finish, slow narration.
5. **Walk through it** — repeat the same demonstration, broken into named
   numbered steps. Errorless: each shown step succeeds.
6. **Recover** — model one realistic failure (misunderstanding, refusal, wrong
   answer) and how the viewer recovers from it. **[L-013, L-016]**
7. **Recap & named win** — explicit, viewer-attributable success: "If you have
   followed along, you have now ___." **[L-006, L-010]**
8. **Soft outro** — what next (the next episode, or "that is the whole topic,
   well done"), and at most one soft mention of Mynaani (see §9).

**C-3.5 — Errorless modelling.** Every shown action in beats 4 and 5 succeeds.
Failures are addressed only in beat 6 (recover) and only with an explicit
recovery path shown. **[L-007]**

**C-3.6 — Concreteness.** Every claim about what the tool can do is paired with
a **shown example** in the same episode. Capabilities are never asserted in the
abstract. **[L-007, L-016]**

**C-3.7 — Cognitive-load discipline.** On-screen text never exceeds **two
simultaneous items**. Numbered steps are surfaced one at a time, with the
previous step's anchor still visible. Working-memory load is bounded to ≤ 4
elements at any moment. **[L-007]**

---

## §4 — Forbidden patterns

The following are **defects** — a script containing any of these fails the
audit (see §11) and does not ship.

**C-4.1** Ageist framing: "for seniors," "even your grandparents can," "despite
your age," "old-fashioned," "back in your day," "kids these days," "tech-savvy
youngsters." **[L-003, L-011, L-014]**

**C-4.2** Deficit framing: "if you struggle with," "for those who find it
hard," "if you're nervous about computers." Replace with resource-reallocation
framing: "here is one focused way to ___." **[L-002, L-005]**

**C-4.3** Caregiver-redirected address: "ask your grandchild to help you," "have
someone younger set this up." The viewer is the operator. **[L-003, L-014]**

**C-4.4** Reassurance theatre: "don't worry," "it's so easy," "anyone can do
this." These erase rather than dismantle anxiety. **[L-010, L-014]**

**C-4.5** Fear / urgency / scarcity: "before it's too late," "while you still
can," "everyone is using this," "you'll be left behind." **[L-014]**

**C-4.6** Discovery-style instruction: "have a look around," "explore the
menu," "see what you can find." Replace with explicit, named steps. **[L-006,
L-007]**

**C-4.7** Abstract capability claims without a shown example. **[L-016]**

**C-4.8** Multi-concept episodes (more than one core thing taught per episode).
**[C-3.3]**

**C-4.9** Hidden costs or risks. Any privacy, money, time, or hallucination
cost that the viewer might reasonably want to know is named in the episode.
**[L-014, L-016]**

**C-4.10** Hard-sell CTAs (see §9 for soft-CTA rules).

**C-4.11** Speech rate above 125 wpm in any 30-second window of the spoken
audio. **[C-3.2, L-001]**

**C-4.12** Use of "guys," "folks" only if the line cannot be rewritten without
condescension. Default address is "you" singular, occasionally "we." Never
"you guys," never "you folks at home."

---

## §5 — Voice & audio

**C-5.1 — Voice character.** A **warm, calm, mid-50s female** voice. Subject to
viewer feedback after the first three pilots, this is provisional but
contract-mandated until amended. The voice never sounds rushed, performative,
or hyped. **[L-010, L-011]**

**C-5.2 — Prosody.** Mean speech rate 110–120 wpm (see C-3.2). Pauses of
**≥ 600 ms** between numbered steps. No upspeak. No "smile in the voice"
performative warmth — sincere is enough. **[L-007]**

**C-5.3 — Loudness.** Programme loudness target **−16 LUFS integrated** ±1 LU
for YouTube delivery; true-peak ceiling −1.5 dBTP. Music beds **−12 LU below
voice** when present. **[L-007]**

**C-5.4 — Music.** Optional, sparing, instrumental, low-tempo. No music during
the show-it / walk-through / recover beats (C-3.4 #4–#6). Music is never
required.

**C-5.5 — Background.** No background noise, no room reverb beyond what TTS
naturally produces, no SFX during instruction.

---

## §6 — Visual & display

**C-6.1 — Format.** Default **1920×1080 16:9** for primary YouTube delivery.
A **1080×1920 9:16** vertical cut may be authored for the same script when
appropriate; the script does not change between cuts. Mobile-readability is
designed for the 16:9 version watched on a 6-inch phone. **[L-015]**

**C-6.2 — Typography.** Sans-serif; on-screen body text **≥ 48 px at 1080p**
(corresponds to roughly 2.5 % of frame height); no thin weights; tracking
generous; leading ≥ 1.4. Headings ≥ 72 px. **[L-007, L-008]**

**C-6.3 — Contrast.** Minimum **7:1** contrast ratio between any displayed
text and its background (WCAG AAA for normal text). No coloured text on
similarly-toned backgrounds. **[L-007, L-008]**

**C-6.4 — Colour.** Colour is never the sole carrier of meaning. Avoid sole
reliance on blue-yellow distinction (age-related lens yellowing). **[L-008]**

**C-6.5 — Motion.** No rapid cuts, no parallax, no auto-zooming, no
auto-advancing carousels. Transitions ≥ 400 ms and ≤ 800 ms. Static
or slow-pan is the default. **[L-008]**

**C-6.6 — On-screen text dwell.** Any on-screen text must remain visible for
**at least 0.4 s per word** (≈ 150 wpm reading rate) plus 1 s buffer, never
less than **3 s total**. **[L-008]**

**C-6.7 — Icons.** Every icon used to convey meaning is paired with a text
label. Novel icon vocabularies are forbidden. **[L-008]**

**C-6.8 — On-screen anchors.** During the walk-through beat (C-3.4 #5), the
current step number and a one-line anchor of the prior step remain visible.
**[L-007]**

**C-6.9 — Faces.** Pilots are faceless. When a human is shown (later phases),
they are an older adult performing the task themselves, never a caregiver or a
younger model. **[L-011, L-014]**

---

## §7 — Captions & accessibility

**C-7.1 — Captions are mandatory.** Every episode ships with burned-in or
sidecar captions (SRT/VTT). YouTube auto-captions alone do **not** satisfy
this clause. **[L-005, L-008]**

**C-7.2 — Caption pacing.** Captions display at a rate calibrated to
**≤ 160 wpm reading speed** (slower than spoken-audio rate to allow re-read).
Each caption line ≤ 42 characters, ≤ 2 lines on screen. **[L-008]**

**C-7.3 — Caption typography.** White text on a 70 %-opacity black box,
sans-serif, ≥ 36 px at 1080p. No drop shadows, no italic-only emphasis.

**C-7.4 — Plain language.** Spoken text targets US English at roughly an
**8th-grade Flesch–Kincaid reading level** unless the topic genuinely requires
a higher level. Jargon is named once, defined once, then used. **[L-005, L-011]**

**C-7.5 — Audio description.** Where visuals carry information not present in
the spoken audio, the narration covers that information in words. There is no
separate audio-description track; the script does the work.

---

## §8 — AI/Claude content rules

These rules apply when the episode topic is an AI capability (asking Claude,
using a voice assistant, evaluating an AI answer, etc.).

**C-8.1 — Conversational modelling.** Every AI episode includes at least
**one full "ask → evaluate → follow up" turn**, not a single isolated prompt.
The script teaches the *conversation*, not the prompt. **[L-013, L-016]**

**C-8.2 — Recovery turn (mandatory in §3 beat 6).** Every AI episode shows
how to recover when the assistant misunderstands, refuses, or gives a wrong
or unhelpful answer. **[L-013, L-016]**

**C-8.3 — Hallucination disclosure.** When a script demonstrates the AI giving
a factual answer, the script explicitly tells the viewer to **verify
consequential facts** elsewhere and shows one concrete way to do so.
**[L-014, L-016]**

**C-8.4 — Privacy disclosure.** Any episode that involves sending personal
information to an AI service names what the service may do with that
information (in plain language) and shows one privacy-preserving alternative
where one exists. **[L-014, L-016]**

**C-8.5 — Cost disclosure.** If the demonstrated capability requires a paid
plan, the script says so, names the price band, and notes whether a free path
exists. **[L-011, L-014]**

**C-8.6 — Trust through small wins.** Early episodes (the first 10) prefer
**concrete, immediately useful queries** (weather, recipes, simple lookups,
drafting a short note) over novelty or abstract capability. **[L-013]**

---

## §9 — CTAs & Mynaani

**C-9.1 — At most one Mynaani reference per episode.** It appears in beat 8
only (soft outro), is **≤ 12 spoken words**, and is never paired with urgency,
discount, scarcity, or fear language.

**C-9.2 — Mynaani is offered, not pushed.** Phrasing pattern:
> "If you would like a guided course on this, Mynaani is one route. The next
> episode here is also free."

A free or self-paced alternative is always named in the same breath.

**C-9.3 — Patent-pending language.** If the script mentions Mynaani's status,
use the phrase **"with a patent-pending learning method"** — never "patented,"
never "trademarked" unless verified, never "the only" or "revolutionary."
Hyperbolic language is forbidden. *(Maintenance task M-002: verify current
USPTO patent-pending status before first publish.)*

**C-9.4 — Subscribe asks.** "Subscribe" is asked at most once per episode, in
beat 8, in one short sentence, and never via fear ("don't miss") or urgency.

**C-9.5 — No external CTAs other than Mynaani and YouTube subscribe.** No
affiliate links, no sponsorships, no third-party product recommendations in
pilots.

---

## §10 — Risk, safety & honesty

**C-10.1 — Health, finance, legal.** Episodes that touch health, finance, or
legal topics state explicitly that the AI's output is **not** professional
advice and that the viewer should consult a qualified professional for
consequential decisions. **[L-014]**

**C-10.2 — Scam-adjacent topics.** When an episode discusses how AI can be
used to detect or avoid scams, it does not also model how scams are
constructed. The line is "spot it" — never "build it."

**C-10.3 — Identity and emotion.** Episodes do not encourage the viewer to
form an emotional bond with the AI, treat it as a friend, or rely on it for
companionship. The AI is a tool. **[L-014]**

**C-10.4 — Children.** Pilots do not address children, and the channel does
not use children's voices, faces, or names without separate consent processes
(out of scope for pilots).

---

## §11 — Compliance & audit

**C-11.1 — Every script is audited.** Before any TTS, b-roll, captioning, or
publishing step runs, the script passes the contract auditor (see
[`audit-rubric.md`](./audit-rubric.md)). The auditor is implemented as a
deterministic pre-check plus a Claude-agent review pass. A failing audit
**blocks** the rest of the pipeline.

**C-11.2 — Audit record.** Each episode directory contains an `audit.json`
listing every clause checked, pass/fail, and the evidence (the offending or
compliant line numbers). Failed audits are not deleted — they are kept in
git so amendments can be traced.

**C-11.3 — Amendments.** This contract is amended only through PRs that meet
the conditions stated in the preamble. Amendments increment the contract
version (semantic versioning of the contract: MAJOR for posture/forbidden-pattern
changes, MINOR for clause additions or relaxations, PATCH for wording).

**C-11.4 — Tie-breaks.** When two clauses appear to conflict, the lower
section number wins (§1 dominates §6, etc.). When a tie-break is invoked,
record it as an ADR under `contract/decisions/`.

**C-11.5 — Contract supremacy over pipeline performance.** A faster, cheaper,
or more impressive production path that breaches any clause is not adopted.
The contract is the optimisation constraint, not the objective.

---

## Appendix A — Citation index (clause → library entries)

| Clause | Library entries |
|---|---|
| §1 Audience | L-001, L-003, L-007, L-011, L-013, L-014, L-015 |
| §2 Editorial posture | L-004, L-010, L-011, L-014, L-016 |
| §3 Script structure & pacing | L-001, L-002, L-006, L-007, L-010, L-013, L-016 |
| §4 Forbidden patterns | L-002, L-003, L-005, L-006, L-007, L-010, L-011, L-014, L-016 |
| §5 Voice & audio | L-007, L-010, L-011 |
| §6 Visual & display | L-007, L-008, L-011, L-014, L-015 |
| §7 Captions & accessibility | L-005, L-008, L-011 |
| §8 AI/Claude content rules | L-013, L-014, L-016 |
| §9 CTAs & Mynaani | L-014 |
| §10 Risk, safety & honesty | L-014 |
| §11 Compliance | (procedural) |

---

## Appendix B — Open items (do not block ratification)

- **M-002 (new):** Verify current USPTO patent-pending status of the Mynaani
  learning method before first publish; if status has lapsed, amend C-9.3.
- **M-003 (new):** Page-level numeric specifications from L-007 and L-008
  (exact pt sizes, contrast ratios, dwell ms) require licensed-PDF verification
  before tightening C-6.2, C-6.6, C-7.2, C-7.3 beyond their current values.
  Current values are conservative and contract-safe; tightening can only make
  the contract stricter, not looser.
- **M-004 (new):** Voice character (C-5.1) is provisional. Re-evaluate after
  three pilots ship and three weeks of viewer signal accumulate.
