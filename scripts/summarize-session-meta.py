#!/usr/bin/env python3
"""Summarize Claude Code session-meta files without emitting full records."""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize Claude Code session metadata.")
    parser.add_argument("session_meta_dir", type=Path)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--limit-recent", type=int, default=30)
    parser.add_argument("--prompt-chars", type=int, default=100)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


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


def truncate(value: Any, limit: int) -> str:
    text = " ".join(str(value or "").split())
    return redact(text)[:limit]


def main() -> int:
    args = parse_args()
    cutoff = dt.datetime.now().timestamp() - args.days * 86400

    if not args.session_meta_dir.is_dir():
        print(f"session_meta_dir_missing: {args.session_meta_dir}")
        return 1

    paths = [
        path
        for path in args.session_meta_dir.glob("*.json")
        if path.stat().st_mtime >= cutoff
    ]
    paths.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    session_types: collections.Counter[str] = collections.Counter()
    projects: collections.Counter[str] = collections.Counter()
    recent: list[tuple[str, str, str, str]] = []

    for path in paths:
        data = load_json(path)
        if not data:
            continue

        session_type = truncate(data.get("session_type") or "unknown", 80)
        project_path = truncate(data.get("project_path") or "unknown", 120)
        session_types[session_type] += 1
        projects[project_path] += 1

        if len(recent) < args.limit_recent:
            date = dt.datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")
            prompt = truncate(data.get("first_prompt"), args.prompt_chars)
            recent.append((date, session_type, project_path, prompt))

    print(f"session_meta_last_{args.days}_days: {len(paths)}")

    print("\nsession_types:")
    for label, count in session_types.most_common(20):
        print(f"- {count} {label}")

    print("\nproject_paths:")
    for label, count in projects.most_common(20):
        print(f"- {count} {label}")

    print("\nrecent_first_prompts:")
    for date, session_type, project_path, prompt in recent:
        print(f"- {date} | {session_type} | {project_path} | {prompt}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
