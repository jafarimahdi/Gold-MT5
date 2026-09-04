"""
test_python_execution.py
========================
Safe unit tests for the Python MT5 execution path.

The fake MT5 module is installed before importing the executor. No real MT5
terminal and no real order are used.

Checks:
  - master switch blocks orders;
  - EA mode blocks the Python executor;
  - same-direction bot positions are not duplicated;
  - opposite bot positions are closed before reversal;
  - manual/other-magic positions are not touched;
  - broker volume rules are applied.
"""

from __future__ import annotations

import sys
import types
from types import SimpleNamespace

# --------------------------------------------------------------------------- #
# Fake MT5 module — must be installed before importing step4_mt5_execution.
# --------------------------------------------------------------------------- #
fake_mt5 = types.ModuleType("MetaTrader5")
fake_mt5.TRADE_ACTION_DEAL = 1
fake_mt5.ORDER_TYPE_BUY = 0
fake_mt5.ORDER_TYPE_SELL = 1
fake_mt5.ORDER_TIME_GTC = 0
fake_mt5.ORDER_FILLING_IOC = 1
fake_mt5.POSITION_TYPE_BUY = 0
fake_mt5.POSITION_TYPE_SELL = 1
fake_mt5.TRADE_RETCODE_DONE = 10009
fake_mt5.TRADE_RETCODE_DONE_PARTIAL = 10010

positions = []
orders = []
account_state = {"equity": 10000.0, "margin_free": 10000.0}


def initialize(**kwargs):
    return True


def shutdown():
    pass


def last_error():
    return (0, "ok")


def symbol_info_tick(symbol):
    return SimpleNamespace(bid=2000.0, ask=2000.2)


def symbol_info(symbol):
    # volume_step deliberately uses 0.10 to prove broker normalization.
    return SimpleNamespace(
        name=symbol, point=0.01, digits=2,
        volume_min=0.10, volume_max=2.00, volume_step=0.10,
        trade_stops_level=0, trade_freeze_level=0, filling_mode=2)


def account_info():
    return SimpleNamespace(**account_state)


def order_calc_margin(order_type, symbol, volume, price):
    return float(volume) * 100.0


def order_check(request):
    return SimpleNamespace(retcode=0)


def positions_get(symbol=None):
    return list(positions)


def order_send(request):
    orders.append(dict(request))
    ticket = 100000 + len(orders)
    if "position" in request:
        positions[:] = [p for p in positions
                        if getattr(p, "ticket", None) != request["position"]]
    else:
        positions.append(SimpleNamespace(
            ticket=ticket, symbol=request["symbol"], type=request["type"],
            volume=request["volume"], magic=request["magic"]))
    return SimpleNamespace(retcode=10009, order=ticket, deal=ticket + 1000)


fake_mt5.initialize = initialize
fake_mt5.shutdown = shutdown
fake_mt5.last_error = last_error
fake_mt5.symbol_info_tick = symbol_info_tick
fake_mt5.symbol_info = symbol_info
fake_mt5.account_info = account_info
fake_mt5.order_calc_margin = order_calc_margin
fake_mt5.order_check = order_check
fake_mt5.positions_get = positions_get
fake_mt5.order_send = order_send
sys.modules["MetaTrader5"] = fake_mt5

import config
from step2_market_analysis import _synthetic_market_data, analyze_market
from step3_ai_decision import Decision
from step4_mt5_execution import MT5Executor

PASS, FAIL = [], []


def check(name, condition):
    (PASS if condition else FAIL).append(name)


def make_snapshot():
    return analyze_market(_synthetic_market_data())


def reset():
    positions.clear()
    orders.clear()
    account_state["equity"] = 10000.0
    account_state["margin_free"] = 10000.0
    config.TRADING_ENABLED = True
    config.EXECUTION_MODE = "python"


def main():
    snap = make_snapshot()
    decision = Decision("BUY", 85.0, "test")
    executor = MT5Executor()

    # Master switch must block before any MT5 operation.
    reset()
    config.TRADING_ENABLED = False
    result = executor.execute(decision, snap)
    check("TRADING_ENABLED=0 blocks order", result.status == "SKIPPED")
    check("disabled mode sends no order", len(orders) == 0)

    # EA mode must never call the Python order path.
    reset()
    config.EXECUTION_MODE = "ea"
    result = executor.execute(decision, snap)
    check("EA mode blocks Python executor", result.status == "SKIPPED")
    check("EA mode sends no order", len(orders) == 0)

    # Margin preflight must reject before order_send when free margin is low.
    reset()
    account_state["margin_free"] = 1.0
    result = executor.execute(decision, snap)
    check("insufficient margin is rejected", result.status == "ERROR")
    check("insufficient margin sends no order", len(orders) == 0)

    # Same-direction bot position must not be duplicated.
    reset()
    positions.append(SimpleNamespace(
        ticket=11, symbol="XAUUSD+", type=fake_mt5.POSITION_TYPE_BUY,
        volume=0.10, magic=234000))
    result = executor.execute(decision, snap)
    check("same-direction bot position is idempotent", result.status == "SKIPPED")
    check("same-direction position sends no order", len(orders) == 0)

    # Opposite bot position must be closed, then the requested BUY opened.
    reset()
    positions.append(SimpleNamespace(
        ticket=22, symbol="XAUUSD+", type=fake_mt5.POSITION_TYPE_SELL,
        volume=0.10, magic=234000))
    result = executor.execute(decision, snap)
    check("opposite bot position is reversed", result.status == "EXECUTED")
    check("reversal sends close and open", len(orders) == 2)
    if len(orders) == 2:
        check("close targets opposite ticket", orders[0].get("position") == 22)
        check("close is opposite order type", orders[0].get("type") == fake_mt5.ORDER_TYPE_BUY)
        check("new order is BUY", orders[1].get("type") == fake_mt5.ORDER_TYPE_BUY)

    # A manual/other-magic position must not be closed by this bot.
    reset()
    positions.append(SimpleNamespace(
        ticket=33, symbol="XAUUSD+", type=fake_mt5.POSITION_TYPE_SELL,
        volume=0.10, magic=999001))
    result = executor.execute(decision, snap)
    check("manual position is not touched", result.status == "EXECUTED")
    check("manual position only causes one new order", len(orders) == 1)
    check("manual position is not in close request",
          len(orders) == 1 and "position" not in orders[0])

    # Broker volume step is respected.
    if orders:
        check("broker volume follows minimum/step",
              abs((orders[-1].get("volume", 0.0) * 10) % 1) < 1e-9)
        check("broker filling mode is selected",
              orders[-1].get("type_filling") == fake_mt5.ORDER_FILLING_IOC)

    print("=" * 64)
    print("PYTHON EXECUTION TEST RESULTS")
    print("=" * 64)
    for name in PASS:
        print(f"  PASS  {name}")
    for name in FAIL:
        print(f"  FAIL  {name}")
    print("-" * 64)
    print(f"  {len(PASS)}/{len(PASS) + len(FAIL)} checks passed")
    print("=" * 64)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
