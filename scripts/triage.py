#!/usr/bin/env python3
"""Normalize one or more SARIF files into the project's findings JSON schema.

SARIF is the common output of CodeQL, Semgrep, Trivy, Checkov, tfsec, and gitleaks.
This script merges them, maps each result to a normalized severity + CWE, and emits a
list of findings (schema documented in docs/outputs-schema.md) for the severity gate,
the Claude agent, and the notifier to consume.

Usage:
    python scripts/triage.py --repo owner/name --sarif a.sarif --sarif b.sarif --out findings.json
    python scripts/triage.py --repo owner/name --sarif-dir .scan-out --out findings.json
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import sys

# CVSS thresholds — kept in sync with policies/severity-matrix.md and severity_gate.py.
CVSS_CRITICAL = 9.0
CVSS_HIGH = 7.0
CVSS_MEDIUM = 4.0

# SARIF result.level -> normalized severity when no numeric score is present.
LEVEL_MAP = {"error": "high", "warning": "medium", "note": "low", "none": "low"}

CWE_RE = re.compile(r"CWE[-_ ]?(\d+)", re.IGNORECASE)


def severity_from_score(score: float) -> str:
    if score >= CVSS_CRITICAL:
        return "critical"
    if score >= CVSS_HIGH:
        return "high"
    if score >= CVSS_MEDIUM:
        return "medium"
    return "low"


def extract_cwe(*texts: str) -> str:
    """Return the first CWE id found in any of the given strings, else 'CWE-0'."""
    for text in texts:
        if not text:
            continue
        match = CWE_RE.search(text)
        if match:
            return f"CWE-{match.group(1)}"
    return "CWE-0"


def rule_index(run: dict) -> dict:
    """Map ruleId -> rule object from a SARIF run's driver rules (for CWE/severity lookup)."""
    rules = {}
    driver = run.get("tool", {}).get("driver", {})
    for rule in driver.get("rules", []) or []:
        if "id" in rule:
            rules[rule["id"]] = rule
    return rules


def security_severity(result: dict, rule: dict) -> float | None:
    """Pull the numeric security-severity (CVSS-like) from result/rule properties."""
    for source in (result.get("properties", {}), rule.get("properties", {})):
        val = source.get("security-severity") or source.get("security_severity")
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                continue
    return None


def normalize_result(result: dict, rules: dict, repo: str) -> dict:
    rule_id = result.get("ruleId", "unknown")
    rule = rules.get(rule_id, {})

    # Severity: prefer numeric security-severity, fall back to SARIF level.
    score = security_severity(result, rule)
    if score is not None:
        severity = severity_from_score(score)
    else:
        severity = LEVEL_MAP.get(result.get("level", "warning"), "medium")

    # Location (first physical location).
    path, line = "", 0
    locations = result.get("locations") or []
    if locations:
        phys = locations[0].get("physicalLocation", {})
        path = phys.get("artifactLocation", {}).get("uri", "")
        line = phys.get("region", {}).get("startLine", 0)

    message = (result.get("message") or {}).get("text", "")
    rule_desc = (rule.get("fullDescription") or rule.get("shortDescription") or {}).get("text", "")
    tags = " ".join(rule.get("properties", {}).get("tags", []) or [])
    cwe = extract_cwe(rule_id, message, rule_desc, tags)

    raw = f"{repo}:{path}:{line}:{rule_id}"
    finding_id = hashlib.sha1(raw.encode()).hexdigest()[:12]

    return {
        "finding_id": finding_id,
        "repo": repo,
        "path": path,
        "line": line,
        "severity": severity,
        "cwe": cwe,
        "rule_id": rule_id,
        "message": message[:500],
        "suggested_fix": rule_desc[:300] or message[:300],
        "remediation_pr_url": None,
        "ticket_id": None,
    }


def load_sarif(path: str, repo: str) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    findings: list[dict] = []
    for run in doc.get("runs", []) or []:
        rules = rule_index(run)
        for result in run.get("results", []) or []:
            findings.append(normalize_result(result, rules, repo))
    return findings


def dedupe(findings: list[dict]) -> list[dict]:
    seen, out = set(), []
    for f in findings:
        if f["finding_id"] in seen:
            continue
        seen.add(f["finding_id"])
        out.append(f)
    return out


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Normalize SARIF into findings JSON.")
    p.add_argument("--repo", required=True, help="owner/name of the scanned repo")
    p.add_argument("--sarif", action="append", default=[], help="SARIF file (repeatable)")
    p.add_argument("--sarif-dir", help="directory to glob for *.sarif")
    p.add_argument("--out", default="findings.json", help="output path")
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    sarif_files = list(args.sarif)
    if args.sarif_dir:
        sarif_files += glob.glob(os.path.join(args.sarif_dir, "**", "*.sarif"), recursive=True)
    if not sarif_files:
        print("warning: no SARIF inputs; writing empty findings", file=sys.stderr)

    findings: list[dict] = []
    for path in sarif_files:
        if not os.path.exists(path):
            print(f"warning: SARIF not found: {path}", file=sys.stderr)
            continue
        try:
            findings += load_sarif(path, args.repo)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"warning: skipping unreadable SARIF {path}: {exc}", file=sys.stderr)

    findings = dedupe(findings)
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    findings.sort(key=lambda f: order.get(f["severity"], 9))

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(findings, fh, indent=2)

    counts = {s: sum(1 for f in findings if f["severity"] == s) for s in order}
    print(f"wrote {len(findings)} findings to {args.out}: {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
