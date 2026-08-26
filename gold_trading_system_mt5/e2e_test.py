"""
e2e_test.py
===========
End-to-end integration test for the gold trading system.

Verifies the FULL live path by mocking the two external dependencies
(Gemini SDK and MetaTrader5 SDK) so every step's real code runs:

    STEP 1 (demo data) -> STEP 2 (analysis) -> STEP 3 (mock Gemini returns
    BUY@85%) -> STEP 4 (mock MT5 executes order) -> STEP 5 (mock position list)

Also exercises edge paths (HOLD, low confidence, error handling).

Usage:  python3 e2e_test.py
"""

import sys
import types
from types import SimpleNamespace

# --------------------------------------------------------------------------- #
# Install mocks BEFORE importing the steps (they capture imports at load time)
# --------------------------------------------------------------------------- #

# --- mock google-genai ------------------------------------------------------
fake_google = types.ModuleType("google")
fake_genai = types.ModuleType("google.genai")


class _FakeResponse:
    text = '{"action": "BUY", "confidence": 85, "rationale": "strong uptrend"}'


class _FakeModels:
    def generate_content(self, model, contents):
        return _FakeResponse()


class _FakeClient:
    def __init__(self, api_key, **kwargs):
        self.api_key = api_key
        self.models = _FakeModels()

    def close(self):
        pass


fake_genai.Client = _FakeClient
fake_google.genai = fake_genai
sys.modules["google"] = fake_google
sys.modules["google.genai"] = fake_genai

# --- mock MetaTrader5 --------------------------------------------------------
fake_mt5 = types.ModuleType("MetaTrader5")
fake_mt5.TRADE_ACTION_DEAL = 1
fake_mt5.ORDER_TYPE_BUY = 0
fake_mt5.ORDER_TYPE_SELL = 1
fake_mt5.ORDER_TIME_GTC = 0
fake_mt5.ORDER_FILLING_IOC = 1
fake_mt5.POSITION_TYPE_BUY = 0
fake_mt5.POSITION_TYPE_SELL = 1
fake_mt5.TRADE_RETCODE_DONE = 10009


def _initialize(*args, **kwargs):
    # The real provider may pass an explicit terminal path. Accept it in the
    # fake so this test remains independent of the user's broker .env.
    return True


def _shutdown():
    pass


def _symbol_info_tick(symbol):
    return SimpleNamespace(ask=2032.70, bid=2032.50)


def _account_info():
    return SimpleNamespace(equity=10000.0)


def _order_send(request):
    return SimpleNamespace(retcode=10009, order=123456)


fake_positions = []


def _positions_get(symbol=None):
    return list(fake_positions)


def _symbol_info(symbol):
    return SimpleNamespace(
        name=symbol, point=0.01, digits=2,
        volume_min=0.01, volume_max=100.0, volume_step=0.01,
        trade_stops_level=0, trade_freeze_level=0, filling_mode=2)


# ---- data-provider functions (used when DATA_SOURCE=mt5 in Step 1) ----------
fake_mt5.COPY_TICKS_ALL = 1
fake_mt5.TIMEFRAME_M1 = 1
fake_mt5.TIMEFRAME_M5 = 5
fake_mt5.TIMEFRAME_M15 = 15
fake_mt5.TIMEFRAME_M30 = 30
fake_mt5.TIMEFRAME_H1 = 60
fake_mt5.TIMEFRAME_H4 = 240
fake_mt5.TIMEFRAME_D1 = 1440


def _symbol_select(symbol, enable):
    return True


def _market_book_add(symbol):
    return True


def _market_book_release(symbol):
    return True


def _market_book_get(symbol):
    return [SimpleNamespace(type=0, price=2032.0, volume=100),
            SimpleNamespace(type=0, price=2031.9, volume=80),
            SimpleNamespace(type=1, price=2032.6, volume=120),
            SimpleNamespace(type=1, price=2032.7, volume=90)]


def _copy_ticks_from(symbol, since, count, flags):
    return [{"last": 2032.5, "volume": 2, "volume_real": 2, "flags": 32},
            {"last": 2032.4, "volume": 1, "volume_real": 1, "flags": 64},
            {"last": 2032.6, "volume": 3, "volume_real": 3, "flags": 32}]


def _copy_rates_from_pos(symbol, timeframe, start_pos, count):
    base = 2030.0
    return [{"open": base + i, "high": base + i + 1.5, "low": base + i - 0.5,
             "close": base + i + 0.5, "tick_volume": 10, "real_volume": 10}
            for i in range(30)]


fake_mt5.initialize = _initialize
fake_mt5.shutdown = _shutdown
fake_mt5.symbol_info_tick = _symbol_info_tick
fake_mt5.symbol_info = _symbol_info
fake_mt5.account_info = _account_info
fake_mt5.order_send = _order_send
fake_mt5.positions_get = _positions_get
# The real monitor/risk code queries closed deals. Include an empty mocked
# result so the end-to-end test does not emit misleading missing-API warnings.
fake_mt5.history_deals_get = lambda *args, **kwargs: []
fake_mt5.symbol_select = _symbol_select
fake_mt5.market_book_add = _market_book_add
fake_mt5.market_book_release = _market_book_release
fake_mt5.market_book_get = _market_book_get
fake_mt5.copy_ticks_from = _copy_ticks_from
fake_mt5.copy_rates_from_pos = _copy_rates_from_pos
sys.modules["MetaTrader5"] = fake_mt5

# --------------------------------------------------------------------------- #
import os
import config
config.GEMINI_API_KEY = "test-key"          # enable the "live" AI path
# Override the derived multi-key list too. Otherwise a user's real keys from
# .env can leak into this mocked test (even though no real API call is made).
config.GEMINI_API_KEYS = ["test-key"]
os.environ["GEMINI_API_KEY"] = "test-key"   # survive run_pipeline's reload_env()
config.AI_CONFIDENCE_THRESHOLD = 70.0
# This test installs fake Gemini and fake MT5 modules before importing the
# pipeline. It is therefore safe to enable the execution gate for the mock
# order assertions, even when the user's real .env has trading disabled.
config.TRADING_ENABLED = True
# Isolate mock execution settings from the user's personal .env. In
# particular, a live demo test may cap MAX_LOT_SIZE at 0.01, which would make
# the warning-mode size reduction round back to the same minimum volume.
config.RISK_PER_TRADE_PCT = 1.0
config.MAX_LOT_SIZE = 1.0
config.LOT_SIZE = 0.1
config.CONTRACT_SIZE = 100.0
config.ACCOUNT_EQUITY = 10000.0
config.NEWS_REDUCE_SIZE_PCT = 0.5
# The direct order assertions in this test represent Python execution mode.
config.EXECUTION_MODE = "python"

from step1_data_acquisition import DataAcquisition
from step2_market_analysis import analyze_market, _synthetic_market_data
from step3_ai_decision import AIDecisionEngine, Decision
from step4_mt5_execution import MT5Executor
from step5_monitoring import TradeMonitor

PASS, FAIL = [], []
check = lambda name, cond: (PASS if cond else FAIL).append(name)


def main():
    # ---- STEP 1 ----------------------------------------------------------
    data = DataAcquisition(source="demo").acquire_market_data("XAUUSD")
    check("STEP1: demo data has ticks", len(data["tick_data"]) > 0)
    check("STEP1: candles present",
          len(data["candles"]["close"]) > 50 and len(data["candles"]["volume"]) > 50)

    # ---- STEP 2 ----------------------------------------------------------
    snap = analyze_market(data)
    check("STEP2: snapshot built", snap is not None)
    check("STEP2: signal direction valid",
          snap.signal_direction in ("BUY", "SELL", "NEUTRAL"))
    check("STEP2: confidence in [0,100]", 0 <= snap.confidence <= 100)
    check("STEP2: ATR > 0", snap.volatility.atr > 0)
    check("STEP2: macro correlations set", abs(snap.macro.dxy_correlation) <= 1.0)

    # ---- STEP 3 (mock Gemini -> BUY@85) ---------------------------------
    decision = AIDecisionEngine().decide(snap)
    check("STEP3: AI returned BUY", decision.action == "BUY")
    check("STEP3: confidence == 85", decision.confidence == 85.0)
    check("STEP3: rationale parsed",
          "strong uptrend" in decision.rationale)

    # ---- STEP 4 (mock MT5 -> EXECUTED) -----------------------------------
    result = MT5Executor().execute(decision, snap)
    check("STEP4: order executed", result.status == "EXECUTED")
    check("STEP4: order id recorded", result.order_id == 123456)
    check("STEP4: SL below price (BUY)", result.sl < result.price)
    check("STEP4: TP above price (BUY)", result.tp > result.price)

    # ---- STEP 4 edge: low confidence -> SKIPPED --------------------------
    low_conf = Decision("BUY", 60.0, "weak signal")
    r2 = MT5Executor().execute(low_conf, snap)
    check("STEP4: low confidence skipped", r2.status == "SKIPPED")

    # ---- STEP 4 edge: HOLD -> SKIPPED ------------------------------------
    r3 = MT5Executor().execute(Decision("HOLD", 90.0, "no trade"), snap)
    check("STEP4: HOLD skipped", r3.status == "SKIPPED")

    # ---- NEWS-TIME behaviour (BLACKOUT / WARNING) -------------------------
    blackout_snap = analyze_market(_synthetic_market_data(event_minutes=5))
    check("NEWS: blackout detected (5 min before event)",
          blackout_snap.news.news_state == "BLACKOUT")
    check("NEWS: signal forced NEUTRAL in blackout",
          blackout_snap.signal_direction == "NEUTRAL")
    rb = MT5Executor().execute(Decision("BUY", 95.0, "would-be entry"),
                               blackout_snap)
    check("NEWS: Step 4 SKIPS new entries during blackout", rb.status == "SKIPPED")

    warn_snap = analyze_market(_synthetic_market_data(event_minutes=25))
    check("NEWS: warning detected (25 min before event)",
          warn_snap.news.news_state == "WARNING")
    rw = MT5Executor().execute(Decision("BUY", 95.0, "warning entry"), warn_snap)
    check("NEWS: entry still allowed during warning", rw.status == "EXECUTED")
    r_quiet = MT5Executor().execute(Decision("BUY", 95.0, "quiet entry"), snap)
    check("NEWS: stop widened during warning",
          (rw.price - rw.sl) > (r_quiet.price - r_quiet.sl))
    check("NEWS: size reduced during warning", rw.volume < r_quiet.volume)

    # ---- risk-based sizing ------------------------------------------------
    check("SIZING: risk-based lots in (0, MAX]",
          0.0 < r_quiet.volume <= config.MAX_LOT_SIZE)

    # ---- execution ownership: EA mode must block Python order placement ----
    config.EXECUTION_MODE = "ea"
    ea_block = MT5Executor().execute(Decision("BUY", 95.0, "EA path"), snap)
    check("EA mode blocks Python executor", ea_block.status == "SKIPPED")
    config.EXECUTION_MODE = "python"

    # ---- STEP 5 (mock MT5 -> one open position) --------------------------
    fake_positions[:] = [SimpleNamespace(ticket=999, symbol="XAUUSD", type=0,
                                         volume=0.1, magic=999001,
                                         price_open=2020.0, sl=2010.0,
                                         tp=2050.0, profit=12.5)]
    tm = TradeMonitor(poll_seconds=0)
    positions = tm.check_open_trades()
    check("STEP5: found 1 open position", len(positions) == 1)
    check("STEP5: position parsed",
          positions[0]["ticket"] == 999 and positions[0]["symbol"] == "XAUUSD")

    # ---- STEP 5 loop (2 iterations, no sleep) ----------------------------
    counter = {"n": 0}

    def fake_pipeline():
        counter["n"] += 1

    tm.run_loop(fake_pipeline, max_iterations=2)
    check("STEP5: loop ran 2 iterations", counter["n"] == 2)

    # ---- full main.py orchestration with mocks ----------------------------
    import main as main_mod
    # reset the anti-overtrading state so this test is repeatable
    try:
        from trade_guard import TradeGuard
        TradeGuard().reset()
    except Exception:
        pass
    # disable the AI throttle so the full pipeline exercises the Gemini path.
    # (reload_env() re-reads .env, which would override these, so we neutralise
    # it for this test run.)
    config.AI_MIN_SIGNAL_STRENGTH = 0.0
    config.AI_MIN_INTERVAL_MINUTES = 0
    main_mod._LAST_AI_CALL = 0.0
    import step2_market_analysis as _s2  # noqa: F401  (keep import surface)
    _orig_reload = config.reload_env
    config.reload_env = lambda: None
    main_mod.setup_logging()
    try:
        main_mod.run_pipeline()
    finally:
        config.reload_env = _orig_reload
    # STATUS holds (label, status) tuples; key on the short step name.
    statuses = {s.split("  ")[0].strip(): st for s, st in main_mod.STATUS}
    check("MAIN: step1 OK", statuses.get("STEP 1", "").startswith("OK (mt5"))
    check("MAIN: step2 OK", statuses.get("STEP 2", "").startswith("OK"))
    check("MAIN: step3 BUY", "BUY" in statuses.get("STEP 3", ""))
    check("MAIN: step4 EXECUTED", statuses.get("STEP 4", "").startswith("EXECUTED"))

    # ---- report -----------------------------------------------------------
    print("\n" + "=" * 60)
    print("END-TO-END TEST RESULTS")
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
