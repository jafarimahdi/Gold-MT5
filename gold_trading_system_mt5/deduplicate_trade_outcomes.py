"""
deduplicate_trade_outcomes.py
==============================
Inspect and optionally clean duplicate rows from data/trade_outcomes.csv.

The old logger appended all closed MT5 deals on every loop. The current logger
prevents new duplicates, while this utility safely cleans the old local file.
It never connects to MT5 and never touches source code.

Usage:
    python deduplicate_trade_outcomes.py          # inspect only
    python deduplicate_trade_outcomes.py --apply  # backup then rewrite unique rows
"""

from __future__ import annotations

import argparse
import csv
import shutil
from datetime import datetime
from pathlib import Path

import config


def outcome_key(row: dict) -> tuple:
    """Identity used for the legacy CSV where deal IDs may be unavailable."""
    return tuple((row.get(k) or "").strip() for k in (
        "order_id", "symbol", "side", "pnl", "exit_price"))


def read_rows(path: Path) -> tuple[list, list]:
    with path.open("r", newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return list(reader), list(reader.fieldnames or [])


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean duplicate trade outcomes")
    parser.add_argument("--apply", action="store_true",
                        help="backup and rewrite the CSV with unique rows")
    args = parser.parse_args()

    path = config.DATA_DIR / "trade_outcomes.csv"
    if not path.exists():
        print(f"No file found: {path}")
        return 0

    try:
        rows, fields = read_rows(path)
    except (OSError, csv.Error) as exc:
        print(f"Could not read {path}: {exc}")
        return 1

    seen = set()
    unique = []
    duplicate_count = 0
    for row in rows:
        key = outcome_key(row)
        if key in seen and any(key):
            duplicate_count += 1
            continue
        seen.add(key)
        unique.append(row)

    print(f"File: {path}")
    print(f"Rows before: {len(rows)}")
    print(f"Unique rows: {len(unique)}")
    print(f"Duplicates: {duplicate_count}")

    if not args.apply or duplicate_count == 0:
        print("No file changes made.")
        return 0

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_name(f"{path.name}.backup-{stamp}")
    try:
        shutil.copy2(path, backup)
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields)
            writer.writeheader()
            writer.writerows(unique)
    except (OSError, csv.Error) as exc:
        print(f"Could not rewrite {path}: {exc}")
        return 1

    print(f"Backup created: {backup}")
    print(f"Cleaned file: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
