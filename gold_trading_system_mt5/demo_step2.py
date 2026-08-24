"""
demo_step2.py
=============
End-to-end demo + unit checks of STEP 2 (Enhanced Market Data Collection).

Runs the full analyze_market() pipeline on synthetic gold data, then:
  1. prints the human-readable MarketSnapshot,
  2. saves the full snapshot as JSON under data/,
  3. shows a per-analyzer unit-test pass/fail summary (incl. L2/L3/news-time),
  4. demonstrates the news-time state machine (QUIET / WARNING / BLACKOUT).

Usage:  python3 demo_step2.py
"""

import sys
from datetime import datetime, timedelta, timezone

import numpy as np

from step2_market_analysis import (
    analyze_market,
    format_snapshot,
    snapshot_to_json,
    EconomicCalendar,
    TechnicalAnalyzer,
    OrderFlowAnalyzer,
    OrderBookDepthAnalyzer,
    FootprintBuilder,
    Level3OrderBookAnalyzer,
    VolumeProfileAnalyzer,
    MacroAnalyzer,
    NewsAnalyzer,
    _synthetic_market_data,
)


def unit_checks():
    """Small assertions per analyzer so regressions are caught immediately."""
    results = []
    ok = lambda name, cond: results.append((name, bool(cond)))

    # TechnicalAnalyzer
    ta = TechnicalAnalyzer()
    close = np.array([100 + i * 0.5 + 3 * np.sin(i / 5) for i in range(80)])
    high = close + 2
    low = close - 2
    atr = ta.compute_atr(high, low, close)
    bb_u, bb_m, bb_l = ta.compute_bollinger_bands(close)
    adx, pdi, mdi = ta.compute_adx(high, low, close)
    macd, sig, hist = ta.compute_macd(close)
    rsi = ta.compute_rsi(close)
    ok("ATR > 0", atr > 0)
    ok("Bollinger: upper >= middle >= lower", bb_u >= bb_m >= bb_l)
    ok("ADX in [0,100]", 0 <= adx <= 100)
    ok("MACD histogram == macd - signal", abs((macd - sig) - hist) < 1e-9)
    ok("RSI in [0,100]", 0 <= rsi <= 100)

    # OrderFlowAnalyzer (incl. tick rule)
    of = OrderFlowAnalyzer()
    ticks = [{"price": 1, "volume": 10, "side": "BUY"},
             {"price": 2, "volume": 4, "side": "SELL"}]
    m = of.analyze_tick_data(ticks, {1999.0: 100}, {2001.0: 50})
    ok("CVD == delta == 6", m.cvd == 6.0 and m.delta == 6.0)
    ok("buying pressure ~ 71.4", abs(m.buying_pressure - 71.43) < 0.05)
    ok("bid/ask ratio == 2", abs(m.bid_ask_ratio - 2.0) < 1e-9)
    # tick rule: unlabeled ticks
    m2 = of.analyze_tick_data([{"price": 100, "volume": 1, "side": ""},
                               {"price": 101, "volume": 1, "side": ""}], {}, {})
    ok("tick rule classifies rising price as BUY",
       m2.tick_rule_classified == 2 and m2.delta == 2.0)

    # OrderBookDepthAnalyzer (LEVEL 2)
    l2a = OrderBookDepthAnalyzer(levels=5)
    bids = {100.0: 50, 99.0: 40}
    asks = {101.0: 30, 102.0: 40}
    micro = l2a.microprice(bids, asks)
    ok("microprice between bid and ask", 100.0 <= micro <= 101.0)
    ok("microprice leans toward ask (bid is thicker)",
       micro > 100.5)
    imb = l2a.depth_imbalance(bids, asks)
    ok("depth imbalance positive when bids thicker", imb > 0)
    l2a.update(bids, asks)
    l2a.update({100.0: 60, 99.0: 40}, {101.0: 30, 102.0: 40})  # bids grew
    ok("OFI positive when bids added", l2a.cumulative_ofi > 0)

    # FootprintBuilder
    fb = FootprintBuilder(price_resolution=1.0)
    fp = fb.build_footprint([{"price": 100, "volume": 5, "side": "BUY"},
                             {"price": 100, "volume": 2, "side": "SELL"},
                             {"price": 101, "volume": 1, "side": "BUY"}])
    ok("dominant level == 100", fp.dominant_level == 100.0)
    ok("strength == 7/8", abs(fp.footprint_strength - 7 / 8) < 1e-9)
    ok("footprint delta imbalance == 4/8", abs(fp.delta_imbalance - 0.5) < 1e-9)

    # Level3OrderBookAnalyzer (LEVEL 3)
    l3 = Level3OrderBookAnalyzer()
    l3.process_order_event({"type": "NEW", "side": "BUY", "price": 100, "size": 5})
    l3.process_order_event({"type": "FILL", "side": "BUY", "price": 100,
                            "size": 2, "is_market_order": True})
    l3.update_order_book([(100, 10), (99, 20)], [(101, 15), (102, 5)])
    lev = l3.analyze()
    ok("market orders == 1", lev.market_orders == 1)
    ok("imbalance == (30-20)/50", abs(lev.order_book_imbalance - 0.2) < 1e-9)
    ok("aggressive buys == 1", lev.aggressive_buys == 1)
    ok("aggressor flow ratio == 1.0 (only buys)", lev.aggressive_flow_ratio == 1.0)
    ok("L3 OFI positive (market buy lifted asks)", lev.ofi > 0)

    # Level3: iceberg detection (repeated NEW same price/size)
    l3b = Level3OrderBookAnalyzer()
    for _ in range(3):
        l3b.process_order_event({"type": "NEW", "side": "SELL", "price": 101,
                                 "size": 7.0, "is_market_order": False})
    ok("iceberg detected on repeated same-size orders", l3b.iceberg_events >= 2)

    # VolumeProfileAnalyzer (VWAP bands)
    vpa = VolumeProfileAnalyzer()
    vpm = vpa.analyze(high, low, close, np.ones(80) * 10)
    ok("VWAP within [low, high]", low.min() <= vpm.vwap <= high.max())
    ok("POC within [low, high]", low.min() <= vpm.poc <= high.max())
    ok("value area low <= POC <= high",
       vpm.value_area_low <= vpm.poc <= vpm.value_area_high)
    ok("VWAP z-score > 0 when price above VWAP",
       close[-1] > vpm.vwap and vpm.vwap_zscore > 0)

    # MacroAnalyzer (log-return correlation)
    ma = MacroAnalyzer()
    mac = ma.analyze({"usd_index": 103, "us_10y_yield": 4.2, "vix_index": 28,
                      "inflation_expectation": 2.3,
                      "gold_series": close, "usd_series": 1.0 / close})
    ok("DXY correlation == -1 (log-returns)", abs(mac.dxy_correlation + 1.0) < 1e-6)
    ok("real yield == 1.9", abs(mac.real_yields - 1.9) < 1e-9)
    ok("VIX 28 -> RISK_OFF", mac.risk_sentiment == "RISK_OFF")

    # NewsAnalyzer
    na = NewsAnalyzer()
    score, label = na.analyze_headlines(
        ["Gold rallies to record high", "Dollar plunges on rate cut bets"])
    ok("bullish headline score > 0", score > 0)
    ok("label == BULLISH", label == "BULLISH")

    # EconomicCalendar + news-time state
    ec = EconomicCalendar()
    events = ec.get_upcoming_events()
    ok("calendar returns >= 1 event", len(events) >= 1)
    etype, impact = ec.classify(events)
    ok("classify returns impact", impact in ("HIGH", "MEDIUM", "LOW"))

    now = datetime.now(timezone.utc)
    ev = [{"title": "FOMC", "impact": "HIGH",
           "date": (now + timedelta(minutes=5)).isoformat()}]
    st, mins, _ = ec.news_state(ev, now=now)
    ok("news_state BLACKOUT within 5 min", st == "BLACKOUT")
    ev2 = [{"title": "CPI", "impact": "HIGH",
            "date": (now + timedelta(minutes=20)).isoformat()}]
    st2, _, _ = ec.news_state(ev2, now=now)
    ok("news_state WARNING at 20 min", st2 == "WARNING")
    ev3 = [{"title": "NFP", "impact": "HIGH",
            "date": (now + timedelta(hours=6)).isoformat()}]
    st3, mins3, _ = ec.news_state(ev3, now=now)
    ok("news_state QUIET far away", st3 == "QUIET" and mins3 > 300)

    return results


def main():
    print("=" * 72)
    print("STEP 2 — ENHANCED MARKET DATA COLLECTION & ANALYSIS — DEMO")
    print("=" * 72)

    # 1) unit checks
    print("\n[1/4] Unit checks ...")
    results = unit_checks()
    failures = [name for name, passed in results if not passed]
    for name, passed in results:
        print(f"   {'PASS' if passed else 'FAIL'}  {name}")
    print(f"   -> {len(results) - len(failures)}/{len(results)} passed")

    # 2) full pipeline (quiet news)
    print("\n[2/4] Running analyze_market() on synthetic XAUUSD data ...")
    data = _synthetic_market_data()
    snapshot = analyze_market(data)
    print(format_snapshot(snapshot))

    # 3) save JSON
    from pathlib import Path
    data_dir = Path(__file__).resolve().parent / "data"
    data_dir.mkdir(exist_ok=True)
    path = data_dir / "market_snapshot.json"
    path.write_text(snapshot_to_json(snapshot))
    print(f"\n[3/4] Full snapshot saved -> {path} ({len(json_out := path.read_text())} bytes)")

    # 4) news-time state demo
    print("\n[4/4] NEWS-TIME STATE machine (what the bot does around news):")
    now = datetime.now(timezone.utc)
    # `minutes` is the event offset relative to now: + = event in the future
    for label, minutes in (("25 min before FOMC", +25),
                           ("10 min before FOMC", +10),
                           ("5 min before FOMC", +5),
                           ("30 min after FOMC", -30),
                           ("2 hours after FOMC", -120)):
        event_dt = now + timedelta(minutes=minutes)
        ev = [{"title": "FOMC Interest Rate Decision", "impact": "HIGH",
               "date": event_dt.isoformat()}]
        state, mins_to, title = EconomicCalendar().news_state(ev, now=now)
        action = {"BLACKOUT": "NO NEW TRADES (flat)",
                  "WARNING": "reduce size + widen stops",
                  "QUIET": "trade normally"}[state]
        print(f"   {label:<20} -> {state:8} | bot action: {action} "
              f"(event in {mins_to:+.0f} min)")

    print("\nDone. Exiting "
          f"{'WITH FAILURES' if failures else 'successfully'}.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
