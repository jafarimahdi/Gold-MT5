"""
test_reports.py
===============
Checks that old repeated trade-outcome rows do not inflate report statistics.
No MT5 connection and no file rewrite are used.
"""

from __future__ import annotations

import sys

from robot_report import _dedupe_outcomes


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
    ok = len(clean) == 2
    print("=" * 64)
    print("REPORT DEDUPLICATION TEST RESULTS")
    print("=" * 64)
    print(f"  {'PASS' if ok else 'FAIL'}  duplicate outcome is counted once")
    print("-" * 64)
    print(f"  {1 if ok else 0}/1 checks passed")
    print("=" * 64)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
