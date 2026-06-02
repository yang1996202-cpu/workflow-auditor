#!/usr/bin/env python3
"""Summarize Claude Code projects JSONL files without loading full transcripts."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize Claude Code project sessions.")
    parser.add_argument("projects_dir", type=Path)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--limit-projects", type=int, default=30)
    parser.add_argument("--limit-sessions", type=int, default=20)
    parser.add_argument("--prompt-chars", type=int, default=100)
    return parser.parse_args()


SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]{20,}"),
]


def redact(value: str) -> str:
    text = value
    for pattern in SECRET_PATTERNS:
        text = pattern.sub(lambda m: f"{m.group(1)}[REDACTED]" if m.groups() else "[REDACTED]", text)
    return text


def first_user_text(path: Path, limit: int) -> str:
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    obj: dict[str, Any] = json.loads(line)
                except Exception:
                    continue
                if obj.get("type") != "user":
                    continue
                message = obj.get("message")
                if not isinstance(message, dict):
                    continue
                content = message.get("content")
                if not isinstance(content, list):
                    continue
                texts = [
                    part.get("text", "")
                    for part in content
                    if isinstance(part, dict) and part.get("type") == "text"
                ]
                text = " ".join(t.strip() for t in texts if t).strip()
                if text:
                    return redact(" ".join(text.split()))[:limit]
    except Exception:
        return ""
    return ""


def main() -> int:
    args = parse_args()
    cutoff = dt.datetime.now().timestamp() - args.days * 86400

    if not args.projects_dir.is_dir():
        print(f"projects_dir_missing: {args.projects_dir}")
        return 1

    print("project_activity:")
    project_rows: list[tuple[float, str, int, str]] = []
    for project_dir in args.projects_dir.iterdir():
        if not project_dir.is_dir():
            continue
        sessions = list(project_dir.glob("*.jsonl"))
        if not sessions:
            continue
        latest = max(path.stat().st_mtime for path in sessions)
        latest_date = dt.datetime.fromtimestamp(latest).strftime("%Y-%m-%d")
        project_rows.append((latest, project_dir.name, len(sessions), latest_date))

    for _, name, count, latest_date in sorted(project_rows, reverse=True)[: args.limit_projects]:
        print(f"- {latest_date} | {count} sessions | {name}")

    print(f"\nrecent_first_prompts_last_{args.days}_days:")
    recent_sessions = [
        path
        for path in args.projects_dir.glob("*/*.jsonl")
        if path.stat().st_mtime >= cutoff
    ]
    recent_sessions.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    for path in recent_sessions[: args.limit_sessions]:
        date = dt.datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")
        prompt = first_user_text(path, args.prompt_chars)
        if prompt:
            print(f"- {date} | {path.parent.name} | {path.name} | {prompt}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
