#!/usr/bin/env python3
"""Summarize Claude Code usage-data facets without emitting full records."""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize Claude Code facets.")
    parser.add_argument("facets_dir", type=Path)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--limit-goals", type=int, default=80)
    parser.add_argument("--limit-recent", type=int, default=30)
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

    if not args.facets_dir.is_dir():
        print(f"facets_dir_missing: {args.facets_dir}")
        return 1

    paths = [
        path
        for path in args.facets_dir.glob("*.json")
        if path.stat().st_mtime >= cutoff
    ]
    paths.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    goals: set[str] = set()
    session_types: collections.Counter[str] = collections.Counter()
    friction: collections.Counter[str] = collections.Counter()
    recent: list[tuple[str, str, str]] = []

    for path in paths:
        data = load_json(path)
        if not data:
            continue

        goal = truncate(data.get("underlying_goal"), 180)
        if goal:
            goals.add(goal)

        session_type = truncate(data.get("session_type") or "unknown", 80)
        session_types[session_type] += 1

        counts = data.get("friction_counts")
        if isinstance(counts, dict):
            for key, count in counts.items():
                try:
                    friction[str(key)] += int(count)
                except Exception:
                    friction[str(key)] += 1

        if len(recent) < args.limit_recent:
            date = dt.datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")
            recent.append((date, session_type, truncate(data.get("brief_summary"), 160)))

    print(f"facet_sessions_last_{args.days}_days: {len(paths)}")

    print("\nunique_goals:")
    for goal in sorted(goals)[: args.limit_goals]:
        print(f"- {goal}")

    print("\nsession_types:")
    for label, count in session_types.most_common(20):
        print(f"- {count} {label}")

    print("\nfriction_counts:")
    for label, count in friction.most_common(20):
        print(f"- {count} {label}")

    print("\nrecent_summaries:")
    for date, session_type, summary in recent:
        print(f"- {date} | {session_type} | {summary}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
