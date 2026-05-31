# Findings output schema

`scripts/triage.py` normalizes the SARIF from every scanner into a single `findings.json`
— a JSON array of finding objects. This is the contract consumed by the severity gate, the
Claude agent prompt, and the notifiers.

## Finding object

| Field | Type | Description |
| ----- | ---- | ----------- |
| `finding_id` | string | Stable 12-char id: `sha1(repo:path:line:rule_id)` — used for ticket dedupe |
| `repo` | string | `owner/name` of the scanned repository |
| `path` | string | Repo-relative file path |
| `line` | integer | 1-based start line (0 if unknown) |
| `severity` | string | `critical` \| `high` \| `medium` \| `low` |
| `cwe` | string | `CWE-###` (first CWE found in rule id/message/tags; `CWE-0` if none) |
| `rule_id` | string | Originating scanner rule id |
| `message` | string | Finding message (≤ 500 chars) |
| `suggested_fix` | string | One-line remediation or short rule description |
| `remediation_pr_url` | string \| null | Filled in by the Claude agent when it opens a fix PR |
| `ticket_id` | string \| null | Filled in by the Jira/ADO notifier (`JIRA-123` / `ADO-456`) |

## Example

```json
[
  {
    "finding_id": "9f2a1c4b7e10",
    "repo": "your-org/payments-api",
    "path": "src/auth/login.py",
    "line": 42,
    "severity": "critical",
    "cwe": "CWE-89",
    "rule_id": "python.lang.security.audit.sql-injection",
    "message": "Possible SQL injection via string-formatted query.",
    "suggested_fix": "Use a parameterized query / prepared statement instead of f-string interpolation.",
    "remediation_pr_url": null,
    "ticket_id": null
  }
]
```

## Severity derivation

1. If a numeric `security-severity` is present on the result or rule, map via CVSS
   thresholds (≥ 9.0 critical, ≥ 7.0 high, ≥ 4.0 medium, else low).
2. Otherwise fall back to SARIF `level`: `error → high`, `warning → medium`,
   `note`/`none → low`.

Thresholds are defined once in `scripts/triage.py` and `policies/severity-matrix.md`.
