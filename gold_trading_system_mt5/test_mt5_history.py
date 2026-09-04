"""
test_mt5_history.py
===================
Read-only unit tests for Pepperstone closed-deal history retrieval.

The fake MT5 module deliberately returns only a balance record for date-range
queries, but returns the real-style open/close pair for a position query. This
matches the behavior observed with Pepperstone position 86160935 and proves
that the monitoring path uses the reliable query and de-duplicates deal IDs.
"""

from __future__ import annotations

import sys
import types
from types import SimpleNamespace


fake_mt5 = types.ModuleType("MetaTrader5")
calls = []


def initialize(**kwargs):
    return True


def shutdown():
    pass


def last_error():
    return (1, "Success")


def history_deals_get(*args, **kwargs):
    calls.append((args, kwargs))
    if "position" in kwargs and int(kwargs["position"]) == 86160935:
        opening = SimpleNamespace(
            ticket=57028893, order=86160935, entry=0, type=0,
            magic=234000, position_id=86160935, volume=0.01,
            price=4586.21, commission=-0.04, swap=0.0, profit=0.0,
            symbol="XAUUSD", time_msc=1787786433633)
        closing = SimpleNamespace(
            ticket=57028912, order=86160955, entry=1, type=1,
            magic=234000, position_id=86160935, volume=0.01,
            price=4586.10, commission=-0.04, swap=0.0, profit=-0.11,
            symbol="XAUUSD", time_msc=1787786438676)
        # Return the close twice to prove deal-ticket de-duplication.
        return (opening, closing, closing)
    # A date-range query returns only a balance/deposit record in the test.
    return (SimpleNamespace(
        ticket=57023479, entry=0, type=2, magic=0, position_id=0,
        volume=0.0, price=0.0, commission=0.0, swap=0.0,
        profit=500.0, symbol="", time_msc=1787784511000),)


fake_mt5.initialize = initialize
fake_mt5.shutdown = shutdown
fake_mt5.last_error = last_error
fake_mt5.history_deals_get = history_deals_get
sys.modules["MetaTrader5"] = fake_mt5

import config
from step5_monitoring import TradeMonitor


def main() -> int:
    config.MT5_SYMBOL = "XAUUSD"
    rows = TradeMonitor().check_closed_deals(position_ids={86160935})

    checks = [
        ("position query returned one close row", len(rows) == 1),
        ("close deal ID is retained", rows and rows[0]["deal_id"] == 57028912),
        ("position ID is retained", rows and rows[0]["position_id"] == 86160935),
        ("original entry side is retained", rows and rows[0]["side"] == "BUY"),
        ("net PnL includes commission", rows and rows[0]["pnl"] == -0.15),
        ("position-specific query was used",
         len(calls) == 1 and calls[0][1].get("position") == 86160935),
    ]

    print("=" * 66)
    print("MT5 HISTORY REPORTING TEST RESULTS")
    print("=" * 66)
    for name, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    print("-" * 66)
    print(f"  {sum(ok for _, ok in checks)}/{len(checks)} checks passed")
    print("=" * 66)
    return 0 if all(ok for _, ok in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
