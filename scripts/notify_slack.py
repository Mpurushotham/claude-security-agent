#!/usr/bin/env python3
"""Post a security findings summary to Slack via an incoming webhook.

Reads normalized findings (scripts/triage.py output) and posts a Block Kit message to
SLACK_WEBHOOK_URL. Used for critical/high alerts on PRs and for the daily production digest.

Env:
    SLACK_WEBHOOK_URL   (required) Slack incoming webhook URL

Usage:
    python scripts/notify_slack.py --findings findings.json --repo owner/name --context pr --pr-url https://...
    python scripts/notify_slack.py --findings findings.json --repo owner/name --context digest
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

ORDER = ["critical", "high", "medium", "low"]
EMOJI = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "⚪"}


def load_findings(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return data if isinstance(data, list) else data.get("findings", [])


def build_message(findings: list[dict], repo: str, context: str, pr_url: str | None) -> dict:
    counts = {s: sum(1 for f in findings if f.get("severity") == s) for s in ORDER}
    title = (
        f"Daily security digest — {repo}"
        if context == "digest"
        else f"Security findings — {repo}"
    )
    header = f"{EMOJI['critical']} {title}"

    summary = " · ".join(f"{EMOJI[s]} {s}: {counts[s]}" for s in ORDER)
    blocks: list[dict] = [
        {"type": "header", "text": {"type": "plain_text", "text": header[:150]}},
        {"type": "section", "text": {"type": "mrkdwn", "text": summary}},
    ]

    top = [f for f in findings if f.get("severity") in ("critical", "high")][:10]
    if top:
        lines = [
            f"{EMOJI[f['severity']]} *{f.get('path')}:{f.get('line')}* "
            f"({f.get('cwe')}) — {f.get('message', '')[:140]}"
            for f in top
        ]
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(lines)}})

    if pr_url:
        blocks.append(
            {"type": "section", "text": {"type": "mrkdwn", "text": f"<{pr_url}|View pull request>"}}
        )

    return {"text": f"{title}: {summary}", "blocks": blocks}


def post(webhook: str, payload: dict) -> int:
    req = urllib.request.Request(
        webhook,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"Slack responded {resp.status}")
            return 0
    except urllib.error.URLError as exc:
        print(f"error: Slack post failed: {exc}", file=sys.stderr)
        return 1


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Post findings to Slack.")
    p.add_argument("--findings", default="findings.json")
    p.add_argument("--repo", required=True)
    p.add_argument("--context", default="pr", choices=["pr", "digest"])
    p.add_argument("--pr-url", default=None)
    p.add_argument("--min-severity", default="high", choices=["critical", "high", "medium", "low"])
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    webhook = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook:
        print("SLACK_WEBHOOK_URL not set; skipping Slack notification", file=sys.stderr)
        return 0

    findings = load_findings(args.findings)
    cutoff = ORDER.index(args.min_severity)
    relevant = [f for f in findings if ORDER.index(f.get("severity", "low")) <= cutoff]
    if not relevant and args.context != "digest":
        print("no findings at or above min-severity; nothing to post")
        return 0

    payload = build_message(findings, args.repo, args.context, args.pr_url)
    return post(webhook, payload)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
