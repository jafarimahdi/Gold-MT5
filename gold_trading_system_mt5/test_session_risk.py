"""
test_session_risk.py
====================
Resilience tests: weekend / market-closed / no-data handling, the risk
circuit-breaker, replay provider, and the spread monitor.

This is the suite that answers: "if Rithmic sends nothing (weekend, holiday,
feed drop), will the bot crash or make a big problem?" — the answer must be no.

Usage:  python3 test_session_risk.py
"""

import sys
from datetime import datetime, timedelta, timezone

import config
from session import is_market_open, describe_now, next_open_time
from risk_manager import RiskManager
from spread_monitor import SpreadMonitor
from step2_market_analysis import analyze_market
from step3_ai_decision import Decision
from step4_mt5_execution import MT5Executor

PASS, FAIL = [], []
check = lambda name, cond: (PASS if cond else FAIL).append(name)


def _dt(y, m, d, hh=12, mm=0):
    return datetime(y, m, d, hh, mm, tzinfo=timezone.utc)


def test_session():
    # 2026-08-22 is a Saturday, 2026-08-23 a Sunday, 2026-08-19 a Wednesday
    check("Saturday -> closed", not is_market_open(_dt(2026, 8, 22)))
    check("Sunday -> closed", not is_market_open(_dt(2026, 8, 23)))
    check("Wednesday midday -> open", is_market_open(_dt(2026, 8, 19)))
    check("describe weekend", "WEEKEND" in describe_now(_dt(2026, 8, 22)))
    nxt = next_open_time(_dt(2026, 8, 22))
    check("next_open_time is a weekday", nxt is not None and nxt.weekday() < 5)
    check("next_open_time after now", nxt > _dt(2026, 8, 22))

    # session enforcement can be disabled
    check("enforce=False -> always open", is_market_open(_dt(2026, 8, 22),
                                                         enforce=False) is True)


def test_no_data_does_not_crash():
    # exactly what happens when Rithmic sends nothing: empty dict
    snap = analyze_market({})
    check("empty feed -> snapshot built", snap is not None)
    check("empty feed -> NEUTRAL signal", snap.signal_direction == "NEUTRAL")
    check("empty feed -> zero confidence", snap.confidence == 0.0)
    # Direct executor calls must be safe even if the user's .env enables
    # trading. Force the master switch OFF so this test can never send a real
    # order to a connected MT5 terminal.
    d = Decision("BUY", 95.0, "would-be")
    old_enabled = config.TRADING_ENABLED
    config.TRADING_ENABLED = False
    try:
        r = MT5Executor().execute(d, snap)
    finally:
        config.TRADING_ENABLED = old_enabled
    check("execution on empty snapshot safe", r.status == "SKIPPED")

    # half-empty: candles only (weekend feed that still returns history)
    import numpy as np
    c = {"open": np.linspace(100, 110, 60), "high": np.linspace(100, 110, 60) + 1,
         "low": np.linspace(100, 110, 60) - 1, "close": np.linspace(100, 110, 60),
         "volume": np.full(60, 100.0)}
    s2 = analyze_market({"candles": c, "price": 110.0})
    check("history-only feed safe", s2.signal_direction in ("BUY", "SELL", "NEUTRAL"))


def test_risk_manager():
    rm = RiskManager()
    rm.reset()
    # no losses, no MT5 -> trading allowed
    ok, reason = rm.check(equity=10000.0, now=_dt(2026, 8, 19))
    check("risk: no loss -> allowed", ok)

    # simulate a big daily loss via a persisted state
    now = _dt(2026, 8, 19)
    rm.save_state({"halt_until": (now + timedelta(hours=1)).isoformat(),
                   "reason": "test halt"})
    ok2, reason2 = rm.check(equity=10000.0, now=now)
    check("risk: persisted halt blocks trading", not ok2)
    check("risk: reason includes 'halt'", "halt" in reason2.lower())

    # expired halt -> allowed again
    ok3, _ = rm.check(equity=10000.0, now=now + timedelta(hours=2))
    check("risk: expired halt clears", ok3)
    rm.reset()


def test_replay_provider():
    from data_providers import ReplayProvider, record_market_data, ProviderNotAvailable
    from step2_market_analysis import _synthetic_market_data
    from pathlib import Path

    data = _synthetic_market_data()
    path = config.DATA_DIR / "test_record.json"
    record_market_data(data, path=str(path))

    rp = ReplayProvider(path=str(path))
    replay = rp.acquire("GC")
    check("replay loads ticks", len(replay["tick_data"]) > 0)
    check("replay restores candles as ndarray",
          hasattr(replay["candles"]["close"], "ndim"))
    snap = analyze_market(replay)
    check("replay data runs through Step 2", snap is not None)

    bad = ReplayProvider(path=str(config.DATA_DIR / "does_not_exist.json"))
    try:
        bad.acquire()
        check("missing replay file raises cleanly", False)
    except ProviderNotAvailable:
        check("missing replay file raises cleanly", True)
    path.unlink(missing_ok=True)


def test_spread_monitor():
    m = SpreadMonitor(alert_pct=2.0)
    check("spread: no samples -> not wide", m.is_wide() is False)
    b = m.update(2000.0, 2030.0)      # CFD 1.5% above futures
    check("spread: basis computed", b is not None and abs(b - 1.5) < 1e-9)
    check("spread: 1.5% not wide", m.is_wide() is False)
    m.update(2000.0, 2060.0)          # 3% basis
    check("spread: 3% is wide", m.is_wide() is True)
    check("spread: report string", "WIDE" in m.report())


def main():
    test_session()
    test_no_data_does_not_crash()
    test_risk_manager()
    test_replay_provider()
    test_spread_monitor()

    print("=" * 60)
    print("RESILIENCE TEST RESULTS (weekend / no-data / risk)")
    print("=" * 60)
    for name in PASS:
        print(f"  PASS  {name}")
    for name in FAIL:
        print(f"  FAIL  {name}")
    print("-" * 60)
    print(f"  {len(PASS)}/{len(PASS) + len(FAIL)} checks passed")
    print("=" * 60)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
