"""
test_data_providers.py
======================
Verifies that Rithmic- and Databento-shaped L2/L3 data maps correctly into the
Step-2 schema and flows through analyze_market() without error.

This is the critical compatibility check: whatever transport you wire up, as
long as it forwards callbacks through these mapping functions, the analysis
pipeline (CVD, footprint, L2 depth, L3 events, macro, signal) works.

Usage:  python3 test_data_providers.py
"""

import sys
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import numpy as np

from data_providers import (
    DemoProvider, RithmicProvider, DatabentoProvider, get_provider,
    ProviderNotAvailable, trades_to_candles,
    databento_mbo_row_to_event, databento_mbo_row_to_tick,
    databento_mbp10_row_to_depths, mt5_book_to_depths,
)
from step2_market_analysis import analyze_market
from mt5_signal_bridge import build_signal, signal_to_text, parse_signal

PASS, FAIL = [], []
check = lambda name, cond: (PASS if cond else FAIL).append(name)


def test_mt5_book_types():
    """MT5 real BookInfo type 1/2 values must map to asks/bids correctly."""
    class FakeMT5:
        BOOK_TYPE_SELL = 1
        BOOK_TYPE_BUY = 2

    book = [
        SimpleNamespace(type=1, price=2000.5, volume=10),  # sell/ask
        SimpleNamespace(type=2, price=2000.0, volume=12),  # buy/bid
        SimpleNamespace(type=1, price=2000.6, volume=8),
        SimpleNamespace(type=2, price=1999.9, volume=9),
    ]
    bids, asks = mt5_book_to_depths(book, FakeMT5)
    check("MT5 type 2 maps to bid", bids == {2000.0: 12.0, 1999.9: 9.0})
    check("MT5 type 1 maps to ask", asks == {2000.5: 10.0, 2000.6: 8.0})


def test_factory():
    assert get_provider("demo").name == "demo"
    assert get_provider("rithmic").name == "rithmic"
    assert get_provider("databento").name == "databento"
    try:
        get_provider("bogus")
        check("factory rejects unknown source", False)
    except ValueError:
        check("factory rejects unknown source", True)


def test_databento_mappers():
    # --- MBO row -> order event -------------------------------------------
    ev = databento_mbo_row_to_event(
        {"action": "A", "side": "B", "price": 2000.0, "size": 5})
    check("MBO 'A' -> NEW buy", ev["type"] == "NEW" and ev["side"] == "BUY")
    ev2 = databento_mbo_row_to_event(
        {"action": "T", "side": "A", "price": 2001.0, "size": 3})
    check("MBO 'T' (ask side) -> market SELL fill",
          ev2["type"] == "FILL" and ev2["is_market_order"] is True
          and ev2["side"] == "SELL")
    tick = databento_mbo_row_to_tick(
        {"action": "T", "side": "B", "price": 2001.0, "size": 3})
    check("MBO 'T' -> tick with aggressor side",
          tick == {"price": 2001.0, "volume": 3, "side": "BUY"})
    check("MBO non-trade row -> no tick",
          databento_mbo_row_to_tick({"action": "A"}) is None)

    # --- MBP-10 row -> depths ----------------------------------------------
    row = {"bid_px_00": 2000.0, "bid_sz_00": 10, "bid_px_01": 1999.5,
           "bid_sz_01": 5, "ask_px_00": 2000.5, "ask_sz_00": 8,
           "ask_px_01": 2001.0, "ask_sz_01": 4}
    bids, asks = databento_mbp10_row_to_depths(row, levels=10)
    check("MBP-10 -> bids dict", bids.get(2000.0) == 10 and bids.get(1999.5) == 5)
    check("MBP-10 -> asks dict", asks.get(2000.5) == 8 and asks.get(2001.0) == 4)


def test_rithmic_l2_l3_flow():
    """Simulate Rithmic callbacks (L2 depth + L3 order events) and run Step 2."""
    prov = RithmicProvider()

    # --- LEVEL 2: successive depth snapshots (like Rithmic book updates) ---
    base = 2000.0
    for k in range(5):
        bids = {round(base - i * 0.1, 2): 100 - k * 5 + i for i in range(1, 6)}
        asks = {round(base + i * 0.1, 2): 90 + k * 3 + i for i in range(1, 6)}
        prov.handle_depth(bids, asks)

    # --- LEVEL 3: order events (like Rithmic order callbacks) --------------
    for _ in range(3):
        prov.handle_order_event({"type": "NEW", "side": "BUY", "price": 1999.8,
                                 "size": 5.0, "is_market_order": False})
    prov.handle_order_event({"type": "FILL", "side": "BUY", "price": 2000.1,
                             "size": 3.0, "is_market_order": True})
    prov.handle_order_event({"type": "FILL", "side": "SELL", "price": 2000.2,
                             "size": 2.0, "is_market_order": True})

    # --- L1: trades ---------------------------------------------------------
    now = datetime.now(timezone.utc)
    for i in range(40):
        prov.handle_trade(2000.0 + np.sin(i / 3) * 0.5, 2.0,
                          "BUY" if i % 2 == 0 else "SELL",
                          ts=now - timedelta(minutes=40 - i))

    data = prov.build_market_data(symbol="GC")
    check("rithmic data has L2 depths", len(data["bid_depth"]) > 0)
    check("rithmic data has L3 order events", len(data["order_events"]) >= 5)
    check("rithmic data has book updates", len(data["book_updates"]) == 5)
    check("rithmic data has order book", len(data["order_book"]["bids"]) > 0)
    check("rithmic data has ticks", len(data["tick_data"]) == 40)
    check("rithmic data builds candles", len(data["candles"].get("close", [])) > 0)

    snap = analyze_market(data)
    check("analyze_market() consumes rithmic data", snap is not None)
    check("L3 metrics populated (aggressors)",
          snap.level3.aggressive_buys == 1 and snap.level3.aggressive_sells == 1)
    check("L2 metrics populated (microprice)", snap.order_flow.microprice > 0)
    check("signal valid", snap.signal_direction in ("BUY", "SELL", "NEUTRAL"))


def test_credentials():
    prov = RithmicProvider()
    creds = prov.credentials()
    check("rithmic creds read from config/env",
          "username" in creds and "system" in creds)
    check("rithmic system defaults to paper trading",
          creds["system"] == "Rithmic Paper Trading")
    # without credentials, connect() must raise a clear ProviderNotAvailable
    if not creds["username"]:
        try:
            prov.connect()
            check("rithmic connect fails cleanly without creds", False)
        except ProviderNotAvailable as exc:
            check("rithmic connect fails cleanly without creds",
                  "username" in str(exc) or "RITHMIC" in str(exc))
    else:
        check("rithmic connect fails cleanly without creds", True)


def test_databento_ingest():
    prov = DatabentoProvider()
    # ingest a synthetic MBO row set without touching the network
    prov._ingest_mbo([
        {"action": "A", "side": "B", "price": 2000.0, "size": 5, "ts_event": 1_700_000_000_000_000_000},
        {"action": "T", "side": "B", "price": 2000.1, "size": 2, "ts_event": 1_700_000_060_000_000_000},
    ])
    prov._ingest_mbp10([
        {"bid_px_00": 2000.0, "bid_sz_00": 10, "ask_px_00": 2000.1, "ask_sz_00": 9},
    ])
    data = prov.build_market_data(symbol="GC.n.0")
    check("databento MBO -> order events + ticks",
          len(data["order_events"]) == 2 and len(data["tick_data"]) == 1)
    check("databento MBP-10 -> depths",
          data["bid_depth"].get(2000.0) == 10)
    snap = analyze_market(data)
    check("analyze_market() consumes databento data", snap is not None)


def test_signal_bridge():
    from step2_market_analysis import _synthetic_market_data
    from step3_ai_decision import Decision
    snap = analyze_market(_synthetic_market_data())
    d = Decision("BUY", 85.0, "test")
    sig = build_signal(snap, d)
    text = signal_to_text(sig)
    parsed = parse_signal(text)
    check("signal bridge round-trips direction", parsed["direction"] == "BUY")
    check("signal bridge round-trips confidence",
          abs(float(parsed["confidence"]) - 85.0) < 1e-6)
    check("signal bridge includes SL < price < TP for BUY",
          float(parsed["sl"]) < float(parsed["price"]) < float(parsed["tp"]))
    # blackout -> direction forced NEUTRAL
    from step2_market_analysis import _synthetic_market_data as smd
    b_snap = analyze_market(smd(event_minutes=5))
    b_sig = build_signal(b_snap, d)
    check("signal bridge neutralizes during blackout",
          b_sig["direction"] == "NEUTRAL")


def main():
    test_mt5_book_types()
    test_factory()
    test_databento_mappers()
    test_rithmic_l2_l3_flow()
    test_credentials()
    test_databento_ingest()
    test_signal_bridge()

    print("=" * 60)
    print("DATA-PROVIDER COMPATIBILITY TEST RESULTS")
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
