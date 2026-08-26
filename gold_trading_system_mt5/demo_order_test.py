"""
demo_order_test.py
==================
Explicit, supervised Pepperstone demo order plumbing test.

This does NOT test whether the strategy chose the direction. It deliberately
uses one supplied BUY or SELL decision to verify the broker/execution path.
It requires two safeguards:

    python demo_order_test.py --side BUY --confirm-demo-order

The script requires EXECUTION_MODE=python and TRADING_ENABLED=1 in the local
.env, uses the configured MAX_LOT_SIZE (recommended 0.01), waits briefly, and
then attempts to close only the position owned by this bot's magic number.
It never uses the EA and never closes manual/other-EA positions.

Use only on a demo account. Do not run this while another bot instance is
running. If the process is interrupted after opening, close the bot position
manually in MT5 before continuing.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import config
from step1_data_acquisition import DataAcquisition
from session import is_market_open
from step2_market_analysis import analyze_market
from step3_ai_decision import Decision
from step4_mt5_execution import MT5Executor
from trade_guard import TradeGuard
from risk_manager import RiskManager


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Explicit Pepperstone demo order/close plumbing test")
    parser.add_argument("--side", choices=("BUY", "SELL"), required=True)
    parser.add_argument("--confirm-demo-order", action="store_true",
                        help="required explicit confirmation before sending one demo order")
    parser.add_argument("--hold-seconds", type=int, default=5,
                        help="seconds to wait before the close attempt (default: 5)")
    args = parser.parse_args()

    config.reload_env()
    print("=" * 70)
    print("PEPPERSTONE DEMO ORDER PLUMBING TEST")
    print("=" * 70)
    print(f"Broker: {config.BROKER_NAME or '(not configured)'}")
    print(f"Symbol: {config.MT5_SYMBOL}")
    print(f"Mode: {config.EXECUTION_MODE}")
    print(f"Requested test side: {args.side}")
    print(f"Maximum configured volume: {config.MAX_LOT_SIZE}")
    print("This is a demo order test, not a strategy recommendation.")

    if not args.confirm_demo_order:
        print("ERROR: add --confirm-demo-order to explicitly allow one demo order.")
        return 2
    if config.EXECUTION_MODE != "python":
        print("ERROR: set EXECUTION_MODE=python in the local .env first.")
        return 2
    if not config.TRADING_ENABLED:
        print("ERROR: set TRADING_ENABLED=1 in the local .env for this test only.")
        return 2
    if not is_market_open():
        print("ERROR: configured trading session is closed.")
        return 1

    risk_ok, risk_reason = RiskManager().check()
    if not risk_ok:
        print(f"ERROR: risk manager blocked test: {risk_reason}")
        return 1
    guard_ok, guard_reason = TradeGuard().can_trade()
    if not guard_ok:
        print(f"ERROR: trade guard blocked test: {guard_reason}")
        return 1

    try:
        data = DataAcquisition(source=config.DATA_SOURCE).acquire_market_data()
        if not data.get("has_data", True):
            print("ERROR: MT5 returned no usable data.")
            return 1
        snapshot = analyze_market(data)
        decision = Decision(
            action=args.side,
            confidence=95.0,
            rationale="explicit demo broker plumbing test",
            timestamp=datetime.now(timezone.utc),
        )
        executor = MT5Executor()
        result = executor.execute(decision, snapshot)
        print(f"OPEN RESULT: {result.to_dict()}")
        if result.status != "EXECUTED":
            print("No demo position was opened; no close was attempted.")
            return 1

        TradeGuard().record_trade()
        print(f"Waiting {max(0, args.hold_seconds)} seconds before close attempt...")
        time.sleep(max(0, args.hold_seconds))
        close_results = executor.close_bot_positions()
        print(f"CLOSE RESULT: {close_results}")

        out = config.DATA_DIR / "demo_order_test_result.json"
        out.write_text(json.dumps({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "side": args.side,
            "open": result.to_dict(),
            "close": close_results,
        }, indent=2, default=str), encoding="utf-8")
        print(f"Saved test result -> {out}")
        return 0 if close_results and all(r.get("ok") for r in close_results) else 1
    except Exception as exc:
        print(f"ERROR: demo order test failed: {type(exc).__name__}: {exc}")
        print("If an order was opened before this error, inspect MT5 and close it manually.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
