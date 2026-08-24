"""
test_markets.py
===============
Verifies the market/symbol recognition layer and the price-agnostic execution
anchoring (futures data -> CFD trade) end to end.

Usage:  python3 test_markets.py
"""

import sys

from markets import (normalize_symbol, resolve_market, cross_market_ok,
                     atr_pct, scale_distance)
from step2_market_analysis import analyze_market, _synthetic_market_data
from mt5_signal_bridge import build_signal, parse_signal, signal_to_text
from step3_ai_decision import Decision
import config

PASS, FAIL = [], []
check = lambda name, cond: (PASS if cond else FAIL).append(name)


def test_normalization():
    cases = {
        "GC": "GC", "GCZ4": "GC", "GC.n.0": "GC", "GC=F": "GC",
        "MGC": "MGC", "MGCZ24": "MGC",
        "XAUUSD": "XAUUSD", "XAUUSD.i": "XAUUSD", "XAUUSD.m": "XAUUSD",
        "XAU/USD": "XAUUSD", "GOLD": "XAUUSD", "GOLDUSD": "XAUUSD",
    }
    for raw, expected in cases.items():
        got = normalize_symbol(raw)
        check(f"normalize '{raw}' -> {expected}", got == expected)


def test_resolution():
    prof, notes = resolve_market("GCZ4", "data")
    check("resolve GCZ4 (data) -> GC futures",
          prof.id == "GC" and prof.kind == "futures")
    prof2, _ = resolve_market("XAUUSD.i", "trade")
    check("resolve XAUUSD.i (trade) -> XAUUSD CFD",
          prof2.id == "XAUUSD" and prof2.kind == "cfd")
    try:
        resolve_market("SILVER", "data")
        check("unknown market raises", False)
    except ValueError as exc:
        check("unknown market raises", "SILVER" in str(exc))
    check("GC + XAUUSD is a valid gold pair", cross_market_ok("GC", "XAUUSD"))


def test_price_agnostic_helpers():
    # 1% ATR on a $2000 instrument -> 1.5x stop = $30 at ANY price level
    ap = atr_pct(20.0, 2000.0)
    check("atr_pct == 0.01", abs(ap - 0.01) < 1e-9)
    d1 = scale_distance(ap, 2000.0, 1.5)
    d2 = scale_distance(ap, 2400.0, 1.5)  # different CFD price, same movement
    check("stop distance scales with price (2000)", abs(d1 - 30.0) < 1e-9)
    check("stop distance scales with price (2400)", abs(d2 - 36.0) < 1e-9)


def test_snapshot_market_identity():
    data = _synthetic_market_data()
    data["data_symbol"] = "GC"
    data["data_market"] = "GC"
    data["trade_symbol"] = "XAUUSD"
    data["trade_market"] = "XAUUSD"
    snap = analyze_market(data)
    check("snapshot carries data market", snap.data_market == "GC")
    check("snapshot carries trade market", snap.trade_market == "XAUUSD")
    check("snapshot carries data symbol", snap.data_symbol == "GC")
    check("snapshot carries trade symbol", snap.trade_symbol == "XAUUSD")


def test_signal_bridge_pct():
    snap = analyze_market(_synthetic_market_data())
    d = Decision("BUY", 85.0, "test")
    sig = build_signal(snap, d)
    text = signal_to_text(sig)
    parsed = parse_signal(text)
    sl_pct = float(parsed["sl_pct"])
    tp_pct = float(parsed["tp_pct"])
    check("signal has sl_pct and tp_pct", sl_pct > 0 and tp_pct > sl_pct)
    check("signal trade symbol is XAUUSD (CFD)",
          parsed["trade_symbol"] == "XAUUSD" or parsed["symbol"] == "XAUUSD")

    # The EA math: at a DIFFERENT (CFD) price, SL/TP still reflect the same move
    cfd_price = 2450.0  # hypothetical CFD price, different from futures price
    sl_cfd = cfd_price * (1 - sl_pct / 100.0)
    tp_cfd = cfd_price * (1 + tp_pct / 100.0)
    check("EA-computed SL < CFD price < TP", sl_cfd < cfd_price < tp_cfd)


def test_config_defaults():
    # Broker symbols may have suffixes such as XAUUSD+, XAUUSD.i or XAUUSD.m.
    # Tests should validate the canonical market, not require one exact broker
    # spelling.
    check("MT5 (trade) symbol resolves to XAUUSD",
          normalize_symbol(config.MT5_SYMBOL) == "XAUUSD")
    check("DATA symbol resolves to XAUUSD in the MT5 version",
          normalize_symbol(config.DATA_SYMBOL) == "XAUUSD")


def main():
    test_normalization()
    test_resolution()
    test_price_agnostic_helpers()
    test_snapshot_market_identity()
    test_signal_bridge_pct()
    test_config_defaults()

    print("=" * 60)
    print("MARKET / SYMBOL LAYER TEST RESULTS")
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
