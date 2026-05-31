#!/usr/bin/env python3
"""Create an Azure DevOps work item for each critical/high finding (production repos only).

Uses the Azure DevOps REST API (work item create, JSON Patch document) with a PAT.

Env:
    ADO_ORG_URL   e.g. https://dev.azure.com/your-org
    ADO_PROJECT   project name
    ADO_PAT       personal access token (Work Items: Read & Write)

Usage:
    python scripts/create_ado_workitem.py --findings findings.json --repo owner/name --min-severity high
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
# Azure DevOps priority: 1 (highest) .. 4 (lowest)
ADO_PRIORITY = {"critical": 1, "high": 2, "medium": 3, "low": 4}
API_VERSION = "7.1"


def _env() -> tuple[str, str, str]:
    return (
        os.environ.get("ADO_ORG_URL", "").rstrip("/"),
        os.environ.get("ADO_PROJECT", ""),
        os.environ.get("ADO_PAT", ""),
    )


def _auth_header(pat: str) -> str:
    # ADO basic auth uses an empty username + PAT.
    return "Basic " + base64.b64encode(f":{pat}".encode()).decode()


def create_work_item(org: str, project: str, auth: str, finding: dict, repo: str) -> str | None:
    title = (
        f"[SECURITY][{finding['severity'].upper()}] {finding.get('cwe')} in {repo} "
        f"({finding['finding_id']})"
    )[:250]
    desc = (
        f"<b>Repo:</b> {repo}<br/>"
        f"<b>Location:</b> {finding.get('path')}:{finding.get('line')}<br/>"
        f"<b>Severity:</b> {finding.get('severity')}<br/>"
        f"<b>CWE:</b> {finding.get('cwe')}<br/>"
        f"<b>Rule:</b> {finding.get('rule_id')}<br/><br/>"
        f"<b>Message:</b> {finding.get('message')}<br/><br/>"
        f"<b>Suggested fix:</b> {finding.get('suggested_fix')}"
    )
    patch = [
        {"op": "add", "path": "/fields/System.Title", "value": title},
        {"op": "add", "path": "/fields/System.Description", "value": desc},
        {"op": "add", "path": "/fields/System.Tags", "value": f"security; {finding['severity']}; {finding.get('cwe')}"},
        {"op": "add", "path": "/fields/Microsoft.VSTS.Common.Priority", "value": ADO_PRIORITY.get(finding["severity"], 3)},
    ]
    url = (
        f"{org}/{urllib.parse.quote(project)}/_apis/wit/workitems/"
        f"$Bug?api-version={API_VERSION}"
    )
    req = urllib.request.Request(
        url,
        data=json.dumps(patch).encode(),
        method="POST",
        headers={"Authorization": auth, "Content-Type": "application/json-patch+json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            result = json.loads(resp.read().decode())
            wid = result.get("id")
            print(f"created ADO work item {wid} for finding {finding['finding_id']}")
            return str(wid)
    except urllib.error.HTTPError as exc:
        print(f"error: ADO create failed ({exc.code}): {exc.read().decode()[:300]}", file=sys.stderr)
        return None
    except urllib.error.URLError as exc:
        print(f"error: ADO create failed: {exc}", file=sys.stderr)
        return None


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Create Azure DevOps work items for findings.")
    p.add_argument("--findings", default="findings.json")
    p.add_argument("--repo", required=True)
    p.add_argument("--min-severity", default="high", choices=ORDER)
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    org, project, pat = _env()
    if not all([org, project, pat]):
        print("ADO_* env not fully set; skipping ADO work item creation", file=sys.stderr)
        return 0

    if not os.path.exists(args.findings):
        print("no findings file; nothing to ticket")
        return 0
    with open(args.findings, encoding="utf-8") as fh:
        findings = json.load(fh)

    auth = _auth_header(pat)
    cutoff = ORDER.index(args.min_severity)
    created = 0
    for f in findings:
        if ORDER.index(f.get("severity", "low")) > cutoff:
            continue
        if create_work_item(org, project, auth, f, args.repo):
            created += 1
    print(f"created {created} ADO work item(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
