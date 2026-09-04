"""
test_reports.py
===============
Checks that old repeated trade-outcome rows do not inflate report statistics.
No MT5 connection and no file rewrite are used.
"""

from __future__ import annotations

import sys

from robot_report import _dedupe_outcomes, _split_outcomes


def main() -> int:
    rows = [
        {"order_id": "10", "symbol": "XAUUSD", "side": "BUY",
         "pnl": "1.5", "exit_price": "2001"},
        {"order_id": "10", "symbol": "XAUUSD", "side": "BUY",
         "pnl": "1.5", "exit_price": "2001"},
        {"order_id": "11", "symbol": "XAUUSD", "side": "SELL",
         "pnl": "-0.5", "exit_price": "2002"},
    ]
    clean = _dedupe_outcomes(rows)
    strategy, plumbing = _split_outcomes(
        clean, {"10"})
    ok_dedupe = len(clean) == 2
    ok_split = len(strategy) == 1 and len(plumbing) == 1
    print("=" * 64)
    print("REPORT DEDUPLICATION / CLASSIFICATION TEST RESULTS")
    print("=" * 64)
    print(f"  {'PASS' if ok_dedupe else 'FAIL'}  duplicate outcome is counted once")
    print(f"  {'PASS' if ok_split else 'FAIL'}  plumbing outcome is separate")
    print("-" * 64)
    print(f"  {int(ok_dedupe) + int(ok_split)}/2 checks passed")
    print("=" * 64)
    return 0 if ok_dedupe and ok_split else 1


if __name__ == "__main__":
    sys.exit(main())
