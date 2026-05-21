# Security Policy

## Supported versions

This project is in early development. Only the `main` branch is supported.

## Reporting a vulnerability

If you discover a security vulnerability — including a leaked secret in any commit,
a vulnerable dependency, or a flaw in the publishing pipeline that could allow
unauthorised uploads to the YouTube channel — please report it privately:

1. Open a [GitHub Security Advisory](https://github.com/smiles70/thewiserlearner/security/advisories/new)
   on this repository (preferred).
2. Or contact the maintainer directly via the email in the git history.

Please **do not** open a public issue for security reports.

You can expect:

- Acknowledgement within 72 hours.
- A status update within 7 days.
- Coordinated disclosure once a fix is available.

## Secrets

Secrets (Anthropic API key, Pexels API key, Pixabay API key, Porkbun API keys,
YouTube OAuth tokens) are stored exclusively as [GitHub Actions Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets).
They must never be committed.

Pre-commit hook `gitleaks` and the CI workflow both scan for accidental secret
commits. If a secret is ever pushed:

1. Rotate the secret immediately at the provider.
2. Open a private security advisory.
3. Force-push a clean history if the secret is irrecoverable from logs.
