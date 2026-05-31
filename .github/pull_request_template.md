## Summary

<!-- What does this change do and why? -->

## Type of change

- [ ] Reusable workflow / agent behavior
- [ ] Scanner or gating logic (`scripts/`)
- [ ] Notification integration (Slack / Jira / ADO)
- [ ] Policy / docs
- [ ] OIDC / cloud auth

## Security impact

<!-- Does this change touch gating thresholds, secrets handling, or permissions? -->

## Checklist

- [ ] No secrets, tokens, or credentials committed (the `secret-scan` job must pass)
- [ ] Workflows lint clean (`actionlint .github/workflows/**/*.yml`)
- [ ] Scripts compile (`python -m py_compile scripts/*.py`)
- [ ] Gating thresholds in `scripts/severity_gate.py` stay in sync with `policies/severity-matrix.md`
- [ ] Least-privilege `permissions:` on any new workflow job
- [ ] Cloud auth uses OIDC only — no long-lived credentials
