# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`claude-security-agent` is an enterprise Claude security agent for GitHub, packaged as
**reusable org-level workflows** (`workflow_call`). Downstream repos adopt it with a few
lines; on every PR/push it runs SAST/SCA/IaC/secret scans, has Claude triage the findings,
gates by severity, and escalates critical/high findings to Slack/Jira/ADO.

- **Agent behavior**: defined entirely in `.github/claude-security/claude-security-prompt.md`
  — the single source of truth. Change behavior there, not in workflow YAML.
- **CI/CD**: GitHub Actions. Reusable building blocks under `.github/workflows/reusable/`;
  this repo's own callers at `.github/workflows/*.yml` double as worked examples.
- **Auth**: GitHub Actions → AWS/Azure/GCP via OIDC only — no long-lived cloud credentials.

## Architecture (data flow)

1. `reusable/sast-sca-iac.yml` + `reusable/secret-scan.yml` produce **SARIF**.
2. `scripts/triage.py` normalizes SARIF → `findings.json` (schema in `docs/outputs-schema.md`).
3. `reusable/claude-security-agent.yml` runs `anthropics/claude-code-action@v1` with the
   prompt file; Claude annotates the PR and may open remediation PRs.
4. `scripts/severity_gate.py` decides block/warn/log from `findings.json` (exit code gates merge).
5. `reusable/notify.yml` dispatches Slack / Jira / ADO / GitHub Issue by severity.

## Common commands

```bash
# Lint all workflows (requires actionlint)
actionlint .github/workflows/**/*.yml

# Compile-check scripts
python -m py_compile scripts/*.py

# Triage a SARIF file into normalized findings
python scripts/triage.py --repo owner/name --sarif fixture.sarif --out findings.json

# Run the severity gate (exit 1 if a critical/high finding is present)
python scripts/severity_gate.py --findings findings.json --production true
```

## Conventions

- **No secrets in the repo.** Integrations read from GitHub Actions secrets only
  (`ANTHROPIC_API_KEY`, `SLACK_WEBHOOK_URL`, `JIRA_*`, `ADO_*`). The repo's own
  `secret-scan` job runs against itself.
- **CVSS thresholds** are org-wide constants: `≥ 9.0` critical (block), `7.0–8.9` high,
  `< 7.0` informational. Defined once and reused; mirror them if you add a new scan.
- **Reusable workflows** take typed `inputs` and `secrets: inherit`; callers stay thin.
- **Production repos** (caller passes `production: true`) get stricter gates: 2 approvers
  for critical/high and automatic Jira + ADO ticket creation.
- Severity → gate/approver/ticket mapping lives in `policies/severity-matrix.md`; keep
  `scripts/severity_gate.py` in sync with it.

## When editing

- To change **what the agent flags or how it comments**: edit the prompt file only.
- To change **gating thresholds**: edit `scripts/severity_gate.py` + `policies/severity-matrix.md`.
- To add a **scanner**: add a job to `reusable/sast-sca-iac.yml` that emits SARIF; `triage.py`
  already consumes any SARIF and maps `level`/`security-severity` → normalized severity.
