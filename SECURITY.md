# Security Policy

## Reporting a vulnerability

Report suspected vulnerabilities privately via **GitHub Security Advisories**
(Security → Advisories → *Report a vulnerability*) or by email to the security team. Do
**not** open a public issue for an unpatched vulnerability.

- **Acknowledgement:** within **3 business days**.
- **Triage & severity assignment:** within **5 business days** using CVSS v3.1.
- **Coordinated disclosure:** we will agree a disclosure timeline with the reporter and
  credit reporters who follow this policy.

## Severity & response

This project's own findings follow the same matrix it enforces on others
(`policies/severity-matrix.md`):

| Severity (CVSS) | Response target |
| --------------- | --------------- |
| Critical (≥ 9.0) | Patch within 7 days; block releases until fixed |
| High (7.0–8.9)  | Patch within 30 days |
| Medium (4.0–6.9)| Patch within 90 days |
| Low (< 4.0)     | Tracked in the backlog / digest |

## Secrets

This repository must never contain real credentials. All integrations
(`ANTHROPIC_API_KEY`, `SLACK_WEBHOOK_URL`, `JIRA_*`, `ADO_*`) and all cloud auth use GitHub
Actions secrets or short-lived OIDC tokens. The repo's own `secret-scan` workflow runs
against every push as a backstop.
