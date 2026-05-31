# Severity matrix

Single source of truth for how findings map to gates, approvers, and tickets. Keep
`scripts/severity_gate.py` in sync with this table.

## CVSS → severity (org-wide thresholds)

| CVSS score | Normalized severity |
| ---------- | ------------------- |
| ≥ 9.0      | **critical**        |
| 7.0 – 8.9  | **high**            |
| 4.0 – 6.9  | **medium**          |
| < 4.0      | **low**             |

Findings without a numeric score fall back to SARIF `level`: `error → high`,
`warning → medium`, `note/none → low` (see `scripts/triage.py`).

## Gate, approvers, and tickets

| Severity      | Merge gate                          | Approvers (prod / non-prod) | Ticket                       | Notify           |
| ------------- | ----------------------------------- | --------------------------- | ---------------------------- | ---------------- |
| **Critical**  | **Block** (`exit 1`)                | 2 / 1                       | Auto Jira **and** ADO        | Slack + GH Issue |
| **High**      | **Block** (default threshold)       | 2 / 1                       | Auto Jira **and** ADO        | Slack + GH Issue |
| **Medium**    | Warn — author fixes or accepts risk | 1 / 1                       | Optional                     | Digest           |
| **Low**       | Log only                            | — / —                       | None                         | Daily digest     |

- **Block threshold** is configurable per caller via the `block-threshold` input
  (`critical` | `high` | `medium`); default is `high`.
- **Production repos** (`production: true`) require 2 approvers for critical/high and
  trigger automatic Jira + ADO ticket creation. Non-production repos require 1 approver
  and do not auto-create external tickets.
- Auto-merge is permitted only when all required checks are green and branch protection
  is satisfied (`policies/branch-protection.json`).

## Release gating

A release (`release-gate.yml`) is **blocked** if any unresolved **critical or high**
finding is present in the pre-release scan, regardless of repo type.
