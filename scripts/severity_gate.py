#!/usr/bin/env python3
"""Decide block/warn/log for a run from its normalized findings.

Implements the matrix in policies/severity-matrix.md:

    critical/high -> block merge (exit 1), require 2 approvers, create ticket
    medium        -> warn (exit 0), require 1 approver
    low           -> log only (exit 0), digest

Writes a GitHub Actions step summary / outputs when run in CI (GITHUB_OUTPUT set) and
returns a non-zero exit code when the run must be blocked.

Usage:
    python scripts/severity_gate.py --findings findings.json --production true
    python scripts/severity_gate.py --findings findings.json --block-threshold critical
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def load_findings(path: str) -> list[dict]:
    if not os.path.exists(path):
        print(f"warning: findings file not found: {path}; treating as empty", file=sys.stderr)
        return []
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return data if isinstance(data, list) else data.get("findings", [])


def counts_by_severity(findings: list[dict]) -> dict[str, int]:
    return {sev: sum(1 for f in findings if f.get("severity") == sev) for sev in ORDER}


def required_approvers(counts: dict[str, int], production: bool) -> int:
    if counts["critical"] or counts["high"]:
        return 2 if production else 1
    if counts["medium"]:
        return 1
    return 0


def write_output(key: str, value: str) -> None:
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"{key}={value}\n")


def write_summary(lines: list[str]) -> None:
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Severity gate for security findings.")
    p.add_argument("--findings", default="findings.json")
    p.add_argument("--production", default="false", help="true|false — production repos gate harder")
    p.add_argument(
        "--block-threshold",
        default="high",
        choices=["critical", "high", "medium"],
        help="lowest severity that blocks the merge (default: high)",
    )
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    production = args.production.strip().lower() in ("1", "true", "yes")
    threshold = ORDER[args.block_threshold]

    findings = load_findings(args.findings)
    counts = counts_by_severity(findings)
    approvers = required_approvers(counts, production)

    # Block if any finding is at or above the block threshold severity.
    blocking = [f for f in findings if ORDER.get(f.get("severity"), 9) <= threshold]
    should_block = len(blocking) > 0

    decision = "block" if should_block else ("warn" if counts["medium"] else "pass")

    lines = [
        "## 🛡️ Security severity gate",
        "",
        f"- Production repo: **{production}**",
        f"- Block threshold: **{args.block_threshold}**",
        f"- Findings — critical: **{counts['critical']}**, high: **{counts['high']}**, "
        f"medium: **{counts['medium']}**, low: **{counts['low']}**",
        f"- Required approvers: **{approvers}**",
        f"- Decision: **{decision.upper()}**",
    ]
    if should_block:
        lines.append("")
        lines.append("### Blocking findings")
        for f in blocking[:25]:
            lines.append(
                f"- `{f.get('severity')}` {f.get('path')}:{f.get('line')} "
                f"({f.get('cwe')}) — {f.get('message', '')[:120]}"
            )

    print("\n".join(lines))
    write_summary(lines)
    write_output("decision", decision)
    write_output("required_approvers", str(approvers))
    write_output("critical", str(counts["critical"]))
    write_output("high", str(counts["high"]))
    write_output("blocking", str(len(blocking)))

    return 1 if should_block else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
