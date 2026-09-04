"""
demo_order_test.py
==================
Explicit, supervised Pepperstone demo order plumbing test.

This does NOT test whether the strategy chose the direction. It deliberately
uses one supplied BUY or SELL decision to verify the broker/execution path.
It requires two safeguards:

    python demo_order_test.py --side BUY --confirm-demo-order

The script requires EXECUTION_MODE=python and TRADING_ENABLED=1 in the local
.env, uses the configured MAX_LOT_SIZE (recommended 0.01), verifies that the
position really appears, waits briefly, and then attempts to close only the
position owned by this bot's magic number. It verifies that the position
really disappears and that open/close deals appear in MT5 history. It never
uses the EA and never closes manual/other-EA positions.

Use only on a demo account. Do not run this while another bot instance is
running. If the process is interrupted after opening, close the bot position
manually in MT5 before continuing.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone

import config
from step1_data_acquisition import DataAcquisition
from session import is_market_open
from step2_market_analysis import analyze_market
from step3_ai_decision import Decision
from step4_mt5_execution import MT5Executor
from trade_guard import TradeGuard
from risk_manager import RiskManager


def _live_bot_positions():
    """Read bot-owned positions from the selected MT5 terminal."""
    import MetaTrader5 as mt5
    if not config.mt5_initialize(mt5):
        raise RuntimeError(f"MT5 init failed while verifying position: {mt5.last_error()}")
    try:
        positions = mt5.positions_get(symbol=config.MT5_SYMBOL)
        if positions is None:
            raise RuntimeError(f"positions_get failed: {mt5.last_error()}")
        return [p for p in positions
                if int(getattr(p, "magic", -1) or -1) == 234000]
    finally:
        mt5.shutdown()


def _wait_for_positions(expected: bool, timeout: float = 10.0):
    deadline = time.monotonic() + max(0.0, timeout)
    last = []
    while True:
        last = _live_bot_positions()
        if bool(last) is expected:
            return last
        if time.monotonic() >= deadline:
            return last
        time.sleep(0.25)


def _history_for_positions(position_ids):
    """Read deals by position ID, with a wide-date fallback for MT5 history."""
    import MetaTrader5 as mt5
    if not config.mt5_initialize(mt5):
        raise RuntimeError(f"MT5 init failed while verifying history: {mt5.last_error()}")
    try:
        found = []
        for position_id in position_ids:
            try:
                # Position filtering avoids broker/server timezone issues and
                # is the most reliable way to retrieve the open/close deals.
                found.extend(mt5.history_deals_get(
                    position=int(position_id)) or [])
            except (TypeError, ValueError):
                pass
        if not found:
            # Some older MT5 builds do not support the position keyword. Use a
            # deliberately wide read-only range as a compatibility fallback.
            deals = mt5.history_deals_get(
                datetime(2000, 1, 1), datetime(2100, 1, 1)) or []
            found = [d for d in deals
                     if getattr(d, "position_id", None) in position_ids]
        # De-duplicate a deal returned by more than one position query.
        unique = {}
        for deal in found:
            unique[getattr(deal, "ticket", id(deal))] = deal
        return [d for d in unique.values()
                if getattr(d, "symbol", "") == config.MT5_SYMBOL
                and (getattr(d, "magic", 0) == 234000
                     or getattr(d, "position_id", None) in position_ids)]
    finally:
        mt5.shutdown()


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
        existing = _live_bot_positions()
        if existing:
            print("ERROR: a bot-owned position is already open; close it before testing.")
            return 1

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

        opened_positions = _wait_for_positions(expected=True)
        if not opened_positions:
            print("ERROR: broker reported success but no bot position appeared.")
            return 1
        position_ids = {getattr(p, "ticket", None) for p in opened_positions}
        position_ids.discard(None)
        print(f"VERIFIED OPEN POSITION(S): {sorted(position_ids)}")

        TradeGuard().record_trade()
        print(f"Waiting {max(0, args.hold_seconds)} seconds before close attempt...")
        time.sleep(max(0, args.hold_seconds))
        close_results = executor.close_bot_positions()
        print(f"CLOSE RESULT: {close_results}")

        remaining_positions = _wait_for_positions(expected=False)
        close_verified = not remaining_positions
        history = _history_for_positions(position_ids)
        open_deals = [d for d in history if getattr(d, "entry", None) in (0, 2)]
        close_deals = [d for d in history if getattr(d, "entry", None) in (1, 2)]
        history_verified = bool(open_deals) and bool(close_deals)
        print(f"VERIFIED CLOSED: {close_verified}")
        print(f"HISTORY DEALS: {len(history)} (open={len(open_deals)}, close={len(close_deals)})")

        out = config.DATA_DIR / "demo_order_test_result.json"
        out.write_text(json.dumps({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "side": args.side,
            "open": result.to_dict(),
            "position_ids": sorted(position_ids),
            "close": close_results,
            "close_verified": close_verified,
            "history_deals": len(history),
            "history_deal_ids": sorted({getattr(d, "ticket", None) for d in history
                                         if getattr(d, "ticket", None) is not None}),
            "history_open_deal_ids": sorted({getattr(d, "ticket", None) for d in open_deals
                                              if getattr(d, "ticket", None) is not None}),
            "history_close_deal_ids": sorted({getattr(d, "ticket", None) for d in close_deals
                                               if getattr(d, "ticket", None) is not None}),
            "history_open_deals": len(open_deals),
            "history_close_deals": len(close_deals),
        }, indent=2, default=str), encoding="utf-8")
        print(f"Saved test result -> {out}")
        return 0 if (close_results and all(r.get("ok") for r in close_results)
                      and close_verified and history_verified) else 1
    except Exception as exc:
        print(f"ERROR: demo order test failed: {type(exc).__name__}: {exc}")
        print("If an order was opened before this error, inspect MT5 and close it manually.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
