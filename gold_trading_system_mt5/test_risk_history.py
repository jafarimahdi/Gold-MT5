"""
test_risk_history.py
====================
Checks that the risk manager uses position-specific MT5 history and includes
commission/fees in realised PnL. No real MT5 terminal or orders are used.
"""

from __future__ import annotations

import json
import sys
import tempfile
import types
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace


calls = []
fake_mt5 = types.ModuleType("MetaTrader5")


def initialize(**kwargs):
    return True


def shutdown():
    pass


def last_error():
    return (1, "Success")


def history_deals_get(*args, **kwargs):
    calls.append((args, kwargs))
    if kwargs.get("position") == 86160935:
        return (
            SimpleNamespace(
                ticket=57028893, position_id=86160935, entry=0,
                symbol="XAUUSD", magic=234000, time=1787786433,
                profit=0.0, swap=0.0, commission=-0.04, fee=0.0),
            SimpleNamespace(
                ticket=57028912, position_id=86160935, entry=1,
                symbol="XAUUSD", magic=234000, time=1787786438,
                profit=-0.11, swap=0.0, commission=-0.04, fee=0.0),
        )
    # The date-range path deliberately has no useful XAUUSD rows.
    return ()


fake_mt5.initialize = initialize
fake_mt5.shutdown = shutdown
fake_mt5.last_error = last_error
fake_mt5.history_deals_get = history_deals_get
sys.modules["MetaTrader5"] = fake_mt5

import config
import risk_manager
from risk_manager import RiskManager


def main() -> int:
    config.MT5_SYMBOL = "XAUUSD"
    old_data_dir = config.DATA_DIR
    old_position_file = risk_manager.POSITION_IDS_FILE
    old_plumbing_file = risk_manager.PLUMBING_DEALS_FILE
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        config.DATA_DIR = root
        risk_manager.POSITION_IDS_FILE = root / "tracked_bot_positions.json"
        risk_manager.PLUMBING_DEALS_FILE = root / "plumbing_test_deals.json"
        risk_manager.POSITION_IDS_FILE.write_text(
            json.dumps({"position_ids": [86160935]}), encoding="utf-8")
        now = datetime(2026, 8, 26, 23, 30, tzinfo=timezone.utc)
        value = RiskManager().daily_pnl(now=now)
    config.DATA_DIR = old_data_dir
    risk_manager.POSITION_IDS_FILE = old_position_file
    risk_manager.PLUMBING_DEALS_FILE = old_plumbing_file

    checks = [
        ("risk PnL includes open/close commissions", abs(value - (-0.19)) < 1e-9),
        ("risk used position-specific history",
         len(calls) == 1 and calls[0][1].get("position") == 86160935),
    ]
    print("=" * 66)
    print("RISK MANAGER HISTORY TEST RESULTS")
    print("=" * 66)
    for name, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    print("-" * 66)
    print(f"  {sum(ok for _, ok in checks)}/{len(checks)} checks passed")
    print("=" * 66)
    return 0 if all(ok for _, ok in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
