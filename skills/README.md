# Claude Skills

Claude Skills package a recurring competence as a portable module: a
`SKILL.md` instruction file plus any supporting scripts and resources. Skills
sit alongside agents but are smaller-grained: an agent typically invokes
several skills.

| Skill              | Path                              | Purpose                                                                    |
|--------------------|-----------------------------------|----------------------------------------------------------------------------|
| `contract-audit`   | `contract-audit/SKILL.md`         | Run the agent-side audit pass on a script and return JSON per the rubric   |
| `library-verify`   | `library-verify/SKILL.md`         | Triple-verify a candidate source (OpenAlex + Crossref + publisher page)    |
| `script-rewrite`   | `script-rewrite/SKILL.md`         | Rewrite a script section to fix a specific audit failure                   |
| `plain-language`   | `plain-language/SKILL.md`         | Reduce Flesch–Kincaid grade without changing meaning                       |
| `visual-director`  | `visual-director/SKILL.md`        | Author a `composition.yaml` manifest from a script + voice timings         |
