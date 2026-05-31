#!/usr/bin/env python3
"""Create a Jira issue for each critical/high security finding (production repos only).

Uses the Jira Cloud REST API v3 with basic auth (email + API token). Idempotency is
best-effort: the finding_id is embedded in the summary and a JQL search avoids duplicates.

Env:
    JIRA_BASE_URL   e.g. https://your-org.atlassian.net
    JIRA_USER       account email
    JIRA_TOKEN      API token
    JIRA_PROJECT    project key, e.g. SEC

Usage:
    python scripts/create_jira_ticket.py --findings findings.json --repo owner/name --min-severity high
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

ORDER = ["critical", "high", "medium", "low"]
PRIORITY = {"critical": "Highest", "high": "High", "medium": "Medium", "low": "Low"}


def _env() -> tuple[str, str, str, str]:
    base = os.environ.get("JIRA_BASE_URL", "").rstrip("/")
    user = os.environ.get("JIRA_USER", "")
    token = os.environ.get("JIRA_TOKEN", "")
    project = os.environ.get("JIRA_PROJECT", "")
    return base, user, token, project


def _auth_header(user: str, token: str) -> str:
    raw = f"{user}:{token}".encode()
    return "Basic " + base64.b64encode(raw).decode()


def _request(method: str, url: str, auth: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Authorization": auth, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = resp.read().decode()
        return json.loads(body) if body else {}


def already_exists(base: str, auth: str, project: str, finding_id: str) -> bool:
    jql = f'project = "{project}" AND summary ~ "{finding_id}"'
    url = f"{base}/rest/api/3/search?jql={urllib.parse.quote(jql)}&maxResults=1"
    try:
        result = _request("GET", url, auth)
        return result.get("total", 0) > 0
    except urllib.error.URLError as exc:
        print(f"warning: Jira dedupe search failed: {exc}", file=sys.stderr)
        return False


def adf(text: str) -> dict:
    """Minimal Atlassian Document Format paragraph."""
    return {
        "type": "doc",
        "version": 1,
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}],
    }


def create_issue(base: str, auth: str, project: str, finding: dict, repo: str) -> str | None:
    summary = (
        f"[SECURITY][{finding['severity'].upper()}] {finding.get('cwe')} in {repo} "
        f"({finding['finding_id']})"
    )[:240]
    desc = (
        f"Repo: {repo}\n"
        f"Location: {finding.get('path')}:{finding.get('line')}\n"
        f"Severity: {finding.get('severity')}\n"
        f"CWE: {finding.get('cwe')}\n"
        f"Rule: {finding.get('rule_id')}\n\n"
        f"Message: {finding.get('message')}\n\n"
        f"Suggested fix: {finding.get('suggested_fix')}\n"
    )
    fields = {
        "project": {"key": project},
        "summary": summary,
        "description": adf(desc),
        "issuetype": {"name": "Bug"},
        "labels": ["security", finding["severity"], finding.get("cwe", "CWE-0")],
    }
    try:
        result = _request("POST", f"{base}/rest/api/3/issue", auth, {"fields": fields})
        key = result.get("key")
        print(f"created Jira issue {key} for finding {finding['finding_id']}")
        return key
    except urllib.error.HTTPError as exc:
        print(f"error: Jira create failed ({exc.code}): {exc.read().decode()[:300]}", file=sys.stderr)
        return None
    except urllib.error.URLError as exc:
        print(f"error: Jira create failed: {exc}", file=sys.stderr)
        return None


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Create Jira tickets for findings.")
    p.add_argument("--findings", default="findings.json")
    p.add_argument("--repo", required=True)
    p.add_argument("--min-severity", default="high", choices=ORDER)
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    base, user, token, project = _env()
    if not all([base, user, token, project]):
        print("JIRA_* env not fully set; skipping Jira ticket creation", file=sys.stderr)
        return 0

    if not os.path.exists(args.findings):
        print("no findings file; nothing to ticket")
        return 0
    with open(args.findings, encoding="utf-8") as fh:
        findings = json.load(fh)

    auth = _auth_header(user, token)
    cutoff = ORDER.index(args.min_severity)
    created = 0
    for f in findings:
        if ORDER.index(f.get("severity", "low")) > cutoff:
            continue
        if already_exists(base, auth, project, f["finding_id"]):
            print(f"skip — Jira issue already exists for {f['finding_id']}")
            continue
        if create_issue(base, auth, project, f, args.repo):
            created += 1
    print(f"created {created} Jira issue(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
