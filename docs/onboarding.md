# Onboarding a repo

How any repo in the org adopts the Claude security agent.

## 1. Add the caller workflow

Copy [`examples/consumer-workflow.yml`](../examples/consumer-workflow.yml) into the repo at
`.github/workflows/security.yml`. Replace `<org>` with your GitHub org. Minimal form:

```yaml
name: Security
on:
  pull_request:
  push:
    branches: [main]
permissions:
  contents: write
  pull-requests: write
  issues: write
  security-events: write
  id-token: write
jobs:
  security:
    uses: <org>/claude-security-agent/.github/workflows/reusable-claude-security-agent.yml@main
    with:
      production: true        # stricter gates + auto Jira/ADO
      block-threshold: high
    secrets: inherit
```

`secrets: inherit` forwards the org/repo secrets below to the reusable workflow.

## 2. Configure secrets

Set these as **org-level** secrets (recommended) or per-repo:

| Secret | Required for |
| ------ | ------------ |
| `ANTHROPIC_API_KEY` | Claude review (scans + gate still run without it) |
| `SLACK_WEBHOOK_URL` | Slack alerts |
| `JIRA_BASE_URL`, `JIRA_USER`, `JIRA_TOKEN`, `JIRA_PROJECT` | Jira tickets (production) |
| `ADO_ORG_URL`, `ADO_PROJECT`, `ADO_PAT` | Azure DevOps work items (production) |
| `SEMGREP_APP_TOKEN` | Semgrep (optional, for Semgrep Cloud rules) |

Cloud deploy gating secrets are in [`oidc-setup.md`](oidc-setup.md).

## 3. Enable GitHub Advanced Security

In the repo (or org) settings, enable:

- **CodeQL code scanning** (or rely on this repo's `codeql.yml` caller).
- **Dependabot alerts + security updates.**
- **Secret scanning + push protection.**

## 4. Apply branch protection

Apply the ruleset so the agent's checks are required before merge:

```bash
gh api -X POST repos/<owner>/<repo>/rulesets \
  --input policies/branch-protection.json
```

Edit the `required_status_checks[].context` values in
[`policies/branch-protection.json`](../policies/branch-protection.json) to match the job
names your caller exposes.

## 5. Verify

Open a PR with a deliberate issue (e.g. an f-string SQL query and a fake `AKIA...` token).
Confirm: scanners run, Claude posts line-level comments + a summary, the severity gate
blocks the merge, and a GitHub Issue (plus Slack/Jira/ADO if configured) is created.
