# Repo guide — what every file does

A map of the repository so you know what each file is for and **when you'd edit it**. The
"Edit when" column is the quick answer to "where do I make change X?".

## Directory layout

```
claude-security-agent/
├── .github/
│   ├── claude-security/claude-security-prompt.md   ← agent behavior (the brain)
│   ├── workflows/
│   │   ├── reusable/                                ← building blocks (workflow_call)
│   │   └── *.yml                                    ← this repo's own callers (also examples)
│   ├── CODEOWNERS · dependabot.yml · pull_request_template.md
├── scripts/                                         ← triage, gate, notifiers (Python)
├── policies/                                        ← severity matrix, branch ruleset, OPA
├── docs/                                            ← you are here
├── examples/consumer-workflow.yml                   ← copy this into a consumer repo
├── CLAUDE.md · README.md · SECURITY.md · LICENSE · .gitignore
```

## The brain

| File | What it does | Edit when |
| ---- | ------------ | --------- |
| `.github/claude-security/claude-security-prompt.md` | The **single source of truth** for the agent's behavior — context, ranked goals, rules, output JSON schema, severity gates, notifications. Passed verbatim to `claude-code-action`. | You want to change *what the agent flags or how it comments*. **Start here, not the YAML.** |

## Reusable workflows (`.github/workflows/reusable-*.yml`)

These are the org-level building blocks. Consumer repos `uses:` them with `secrets: inherit`.

| File | What it does | Edit when |
| ---- | ------------ | --------- |
| `claude-security-agent.yml` | **Orchestrator.** Fans out scan → Claude triage → severity gate → notify for a PR/push. The main entry point consumers call. | You add a stage to the pipeline or change orchestration. |
| `sast-sca-iac.yml` | Runs **Semgrep + Trivy + Checkov**, uploads SARIF to the Security tab, and runs `triage.py` to produce `findings.json`. | You add/remove a scanner. (Any SARIF it emits is auto-consumed by triage.) |
| `secret-scan.yml` | **TruffleHog + gitleaks**, full git history; backstops GHAS push protection. | You change secret-scanning behavior. |
| `notify.yml` | Dispatches **Slack / Jira / ADO / GitHub Issue** for high/critical findings (Jira/ADO are production-only). | You add/change an alert channel. |
| `oidc-deploy.yml` | **OIDC-only** cloud auth (AWS/Azure/GCP) for a gated deploy — no static creds. | You change cloud auth or add a cloud. |

## This repo's own callers (`.github/workflows/`)

These run the agent **on this repo itself** and double as worked examples for consumers.

| File | What it does |
| ---- | ------------ |
| `claude-security-review.yml` | Calls `reusable/claude-security-agent.yml` on PR/push/schedule. The canonical example caller. |
| `codeql.yml` | GitHub Advanced Security CodeQL SAST (matrix: python, actions). |
| `dependency-review.yml` | Blocks PRs that introduce vulnerable dependencies. |
| `secret-scan.yml` | Runs the reusable secret scan on this repo. |
| `release-gate.yml` | Severity-gated release: pre-release scan → block on critical/high → SBOM (Syft) + cosign signing → GitHub Release. |

## Scripts (`scripts/`)

Pure Python, no third-party deps (uses only the standard library), runnable locally.

| File | What it does | Edit when |
| ---- | ------------ | --------- |
| `triage.py` | Merges all SARIF → normalized `findings.json`; maps `security-severity`/`level` → severity, extracts CWE, dedupes. | You change the findings schema or severity derivation. |
| `severity_gate.py` | Reads `findings.json`, decides **block/warn/pass**, sets required approver count, writes the GitHub step summary, exits non-zero to block. | You change gating logic (keep in sync with `severity-matrix.md`). |
| `notify_slack.py` | Posts a Block Kit summary to `SLACK_WEBHOOK_URL`. Self-skips if unset. | You change the Slack message. |
| `create_jira_ticket.py` | Creates Jira issues for critical/high (with dedupe). Self-skips if `JIRA_*` unset. | You change Jira fields/behavior. |
| `create_ado_workitem.py` | Creates Azure DevOps work items for critical/high. Self-skips if `ADO_*` unset. | You change ADO fields/behavior. |

## Policies (`policies/`)

| File | What it does | Edit when |
| ---- | ------------ | --------- |
| `severity-matrix.md` | The authoritative mapping: CVSS → severity → gate / approvers / ticket. | You change thresholds (also update `severity_gate.py`). |
| `branch-protection.json` | A GitHub **ruleset** (apply via `gh api`) requiring the agent's checks, approvals, and code-owner review before merge. | You change required checks or approval rules. |
| `opa/no_long_lived_cloud_creds.rego` | Conftest policy that **fails CI** if a workflow uses static AWS keys or an Azure client secret; warns if a cloud-auth job lacks `id-token: write`. | You tighten/loosen the OIDC rule. |
| `opa/owasp_iac.rego` | Baseline OWASP-aligned Terraform guardrails (open ingress, unencrypted storage, missing logging). | You add IaC guardrails. |

## Top-level & meta

| File | What it does |
| ---- | ------------ |
| `README.md` | Project overview, adoption snippet, required secrets, layout. |
| `CLAUDE.md` | Guidance for Claude Code working *in* this repo — commands, conventions, where to edit. |
| `SECURITY.md` | How to report a vulnerability in this repo; its own response SLAs. |
| `.github/CODEOWNERS` | Security team owns prompt, workflows, scripts, policies (required reviewers). |
| `.github/dependabot.yml` | Weekly updates for GitHub Actions + pip. |
| `.github/pull_request_template.md` | PR checklist (no secrets, lint, gate sync, least privilege, OIDC). |
| `examples/consumer-workflow.yml` | Copy-paste workflow a downstream repo drops in to adopt the agent. |
| `.gitignore` | Excludes venvs, scan artifacts (`*.sarif`, `findings*.json`), and any secret files. |

## "I want to change X" → go here

| I want to… | File(s) |
| ---------- | ------- |
| Change what the agent flags / how it comments | `.github/claude-security/claude-security-prompt.md` |
| Change what blocks a merge | `scripts/severity_gate.py` + `policies/severity-matrix.md` |
| Add a scanner | `.github/workflows/reusable-sast-sca-iac.yml` |
| Add/modify an alert channel | `.github/workflows/reusable-notify.yml` + the matching `scripts/*` |
| Add a cloud or change deploy auth | `.github/workflows/reusable-oidc-deploy.yml` + `docs/oidc-setup.md` |
| Change required checks / approvals | `policies/branch-protection.json` |
| Adopt the agent in another repo | `examples/consumer-workflow.yml` + `docs/onboarding.md` |
