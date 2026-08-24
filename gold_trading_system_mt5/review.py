"""
review.py
=========
"Learn from the past" — read the robot's journal and show a simple report.

The bot already saves everything it does:
    - data/decisions_log.csv   -> every decision (signal, AI, news, ...)
    - data/trade_outcomes.csv  -> every closed trade (win/loss)

This script reads those two files and prints the numbers a professional
checks every week: how many trades, win rate, average win vs average loss,
and which confidence levels actually win.

This is the SAFE way to "train" the robot: you look at what really happened,
then we tune the settings (weights, thresholds) and test again on history.
It does NOT rewrite the robot automatically — that would be dangerous with
only a few hundred trades.

Usage:
    python review.py
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import config

DECISIONS = config.DATA_DIR / "decisions_log.csv"
OUTCOMES = config.DATA_DIR / "trade_outcomes.csv"


def _read_csv(path: Path) -> list:
    if not path.exists():
        return []
    with open(path, "r", newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _recent(rows: list, days: int) -> list:
    """Keep only rows whose timestamp is within the last `days` days."""
    if days <= 0:
        return rows
    cutoff = datetime.now() - timedelta(days=days)
    out = []
    for r in rows:
        ts = (r.get("timestamp") or "").strip()
        if not ts:
            out.append(r)
            continue
        try:
            if datetime.fromisoformat(ts) >= cutoff:
                out.append(r)
        except ValueError:
            out.append(r)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Show what the robot has learned from its journal.")
    parser.add_argument("--days", type=int, default=0,
                        help="only look at the last N days (0 = everything)")
    args = parser.parse_args()

    decisions = _recent(_read_csv(DECISIONS), args.days)
    outcomes = _recent(_read_csv(OUTCOMES), args.days)

    span = f"last {args.days} days" if args.days > 0 else "all time"
    print("=" * 62)
    print(f"ROBOT LEARNING REPORT  ({span})")
    print("=" * 62)

    # ---- decisions -------------------------------------------------------
    print(f"\n[1] DECISIONS LOGGED : {len(decisions)} rows")
    if decisions:
        actions = defaultdict(int)
        for d in decisions:
            actions[d.get("ai_action", "?") or "?"] += 1
        for a, n in sorted(actions.items()):
            print(f"      {a:<8} {n}")

    # ---- outcomes ----------------------------------------------------------
    print(f"\n[2] CLOSED TRADES    : {len(outcomes)}")
    if outcomes:
        wins = [float(o["pnl"]) for o in outcomes if float(o.get("pnl") or 0) > 0]
        losses = [float(o["pnl"]) for o in outcomes if float(o.get("pnl") or 0) <= 0]
        total = sum(wins) + sum(losses)
        wr = 100.0 * len(wins) / len(outcomes)
        print(f"      Win rate       : {wr:.1f}%  ({len(wins)}W / {len(losses)}L)")
        print(f"      Avg win        : {sum(wins)/len(wins):+.2f}" if wins else "      Avg win        : -")
        print(f"      Avg loss       : {sum(losses)/len(losses):+.2f}" if losses else "      Avg loss       : -")
        print(f"      Total PnL      : {total:+.2f}")
        if wins and losses:
            pf = sum(wins) / abs(sum(losses))
            print(f"      Profit factor  : {pf:.2f}  (>1 = winning robot)")

        # win rate per side
        sides = defaultdict(lambda: [0, 0, 0.0])
        for o in outcomes:
            s = o.get("side", "?")
            p = float(o.get("pnl") or 0)
            sides[s][0] += 1
            if p > 0:
                sides[s][1] += 1
            sides[s][2] += p
        print("\n      By side:")
        for s, (n, w, p) in sides.items():
            print(f"        {s:<6} {n} trades, {w} wins, PnL {p:+.2f}")

    # ---- advice -------------------------------------------------------------
    print("\n" + "-" * 62)
    if len(outcomes) < 20:
        print("ADVICE: too few closed trades to judge yet (need ~50+).")
        print("        Let it paper-trade on demo for a few weeks first.")
    elif outcomes and wins and losses and sum(wins) / abs(sum(losses)) < 1:
        print("ADVICE: profit factor below 1 — the current settings are losing.")
        print("        Next step: backtest on downloaded history and tune.")
    elif outcomes and wins:
        print("ADVICE: profit factor above 1 — promising! Keep collecting data")
        print("        before trusting it with real money.")
    else:
        print("ADVICE: keep it running; the journal fills up automatically.")
    print("=" * 62)
    return 0


if __name__ == "__main__":
    sys.exit(main())
