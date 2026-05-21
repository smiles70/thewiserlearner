# ADR 0001: Pipeline runtime is GitHub Actions

- **Status:** Accepted
- **Date:** 2026-05-21
- **Deciders:** smiles70

## Context

The pipeline must:

1. Run on a schedule and on demand.
2. Cost $0 / month at v1 scale (~3 videos/month).
3. Require no separately managed infrastructure (no VMs to babysit).
4. Surface failures visibly with minimal monitoring effort.
5. Manage secrets safely.

Three options were considered: GitHub Actions, n8n Cloud, and self-hosted n8n.

## Decision

Use **GitHub Actions**.

## Reasoning

| Criterion | GitHub Actions | n8n Cloud | n8n self-hosted |
|---|---|---|---|
| Cost at v1 scale | $0 (public repo: unlimited) | $20/mo minimum | $0 if free VM, otherwise hosting cost |
| Learning curve | Low (YAML) | Medium (visual nodes) | Medium + VM ops |
| Monitoring | Built-in run UI, email on failure | Built-in | Manual |
| Secrets | Built-in encrypted secrets | Built-in | Manual |
| Reliability | High (Microsoft-grade SLAs) | Medium | Depends |
| Mental model | Same surface as code | Separate surface | Separate surface |

n8n's visual-node strength does not pay off here because every stage in the
pipeline is already a small Python script. We do not need a low-code orchestrator.

## Consequences

- The pipeline lives as YAML workflows in `.github/workflows/` plus Python scripts
  in `pipeline/`.
- Cron triggers are expressed in `schedule:` blocks.
- API credentials (Anthropic, Pexels, Pixabay, Porkbun, YouTube OAuth) live as
  encrypted GitHub Actions secrets.
- We rely on GitHub uptime; if GitHub is down, no episode publishes that day. This
  is acceptable for a content channel.
