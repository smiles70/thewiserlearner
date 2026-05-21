# Agents

Each markdown file in this directory specifies a Claude agent: its role,
inputs, outputs, system-prompt requirements, and the contract clauses it must
honour. These files are loaded by the orchestrator
(`pipeline/run_episode.py`, later parts) and used as the agent's persistent
brief.

## Authoring conventions

- One agent per file, named `<role>.md`.
- YAML front matter records `role`, `model`, `inputs`, `outputs`,
  `contract_clauses` it must obey, and `library_refs` that informed its design.
- The body is the agent's system prompt (or its template, with `{{slots}}`).

## Roles

| Role             | File                        | Purpose                                                       |
|------------------|-----------------------------|---------------------------------------------------------------|
| Researcher       | `researcher.md`             | Source new library candidates and triple-verify them          |
| Scripter         | `scripter.md`               | Draft the eight-beat script for a given episode brief         |
| Auditor          | `auditor.md`                | Run the agent-side checks of `contract/audit-rubric.md`       |
| Voice director   | `voice-director.md`         | Choose voice parameters; supervise prosody and pacing         |
| Visual director  | `visual-director.md`        | Produce the composition manifest (slides, b-roll, text cards) |
| Captioner        | `captioner.md`              | Generate caption text and verify clauses C-7.*                |
| Compositor       | `compositor.md`             | Drive `pipeline/compositor.py` from the manifest              |
| SEO              | `seo.md`                    | Author title/description/tags within contract constraints     |
| Publisher        | `publisher.md`              | Drive `pipeline/youtube.py` upload + thumbnail + playlist     |
| Analyst          | `analyst.md`                | Read YouTube analytics; propose contract amendments           |
