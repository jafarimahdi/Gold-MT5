"""
mt5_test.py
===========
Test your MetaTrader 5 connection and see what FREE data is available.

Run on WINDOWS only, with the MT5 terminal running and logged into a demo
account:

    python mt5_test.py

It shows: the current bid/ask, Level 2 depth (market book), recent ticks
(with buy/sell side) and OHLCV candles — exactly what the MT5Provider feeds
into the analysis engine.

If you see numbers in every section -> your MT5 data feed works.
Then run:  python main.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta

import config


def main() -> int:
    config.reload_env()

    print("=" * 62)
    print("MT5 DATA TEST")
    print("=" * 62)
    print(f"  symbol   : {config.MT5_SYMBOL}")
    print(f"  login    : {config.MT5_LOGIN or '(use running terminal)'}")
    print(f"  password : {'***' if config.MT5_PASSWORD else '(none set)'}")
    print(f"  server   : {config.MT5_SERVER or '(use running terminal)'}")
    print("-" * 62)

    try:
        import MetaTrader5 as mt5
    except ImportError:
        print("ERROR: 'MetaTrader5' package not installed.")
        print("  On Windows run:  pip install MetaTrader5")
        print("  (The MT5 terminal must also be installed and running.)")
        return 1

    if config.MT5_LOGIN:
        ok = mt5.initialize(login=config.MT5_LOGIN,
                            password=config.MT5_PASSWORD,
                            server=config.MT5_SERVER)
    else:
        ok = mt5.initialize()
    if not ok:
        print(f"ERROR: mt5.initialize() failed: {mt5.last_error()}")
        print("  Make sure the MT5 terminal is RUNNING and logged into an")
        print("  account (demo is fine).")
        return 1

    symbol = config.MT5_SYMBOL
    print(f"Connected to terminal. Checking symbol '{symbol}' ...")
    print()

    # ---- 0) find the correct gold symbol --------------------------------
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        print(f"'{symbol}' is not visible in your MT5. Looking for a gold")
        print("symbol among what your broker offers ...")
        print()
        candidates = []
        try:
            all_symbols = mt5.symbols_get()
            for s in (all_symbols or []):
                name = s.name.upper()
                if "XAU" in name or "GOLD" in name:
                    candidates.append(s.name)
        except Exception:
            candidates = []
        if candidates:
            print("Your broker has these gold symbols:")
            for c in sorted(candidates)[:30]:
                print(f"    {c}")
            print()
            print("Fix: set the ONE you trade in .env, e.g.")
            print(f"    MT5_SYMBOL={sorted(candidates)[0]}")
            print()
            print("Also right-click it in MT5 Market Watch so it is visible,")
            print("then run this test again.")
        else:
            print("No gold symbol found among the available symbols.")
            print("Open MT5 -> View -> Symbols (or Ctrl+U), search 'XAUUSD'")
            print("or 'GOLD', add it to Market Watch, then run this test again.")
            print()
            print("If gold is still missing, your demo account may not include")
            print("metals - ask your broker, or open a demo with a broker that")
            print("offers XAUUSD.")
        mt5.shutdown()
        return 1
    print(f"  [1] TICK    : bid={tick.bid}  ask={tick.ask}  last={tick.last}")

    # ---- 2) Level 2 depth ------------------------------------------------
    mt5.symbol_select(symbol, True)
    try:
        mt5.market_book_add(symbol)
        book = mt5.market_book_get(symbol)
        if book:
            print(f"  [2] LEVEL 2 : {len(book)} depth entries (first 5 shown):")
            for e in book[:5]:
                side = "BID" if e.type == 0 else "ASK"
                print(f"          {side}  {e.price} x {e.volume}")
        else:
            print("  [2] LEVEL 2 : empty — your broker may not publish depth")
            print("                for this symbol, or it takes a moment to fill.")
        mt5.market_book_release(symbol)
    except Exception as exc:
        print(f"  [2] LEVEL 2 : error: {exc}")

    # ---- 3) recent ticks (with buy/sell side) ----------------------------
    since = datetime.now() - timedelta(minutes=30)
    ticks = mt5.copy_ticks_from(symbol, since, 2000, mt5.COPY_TICKS_ALL)
    if ticks is not None and len(ticks):
        print(f"  [3] TICKS   : {len(ticks)} ticks in the last 30 min "
              f"(last 3 shown):")
        for t in ticks[-3:]:
            side = "BUY" if t["flags"] & 32 else ("SELL" if t["flags"] & 64 else "?")
            print(f"          last={t['last']}  vol={t['volume']}  side={side}")
    else:
        print("  [3] TICKS   : none in the last 30 min (market closed?)")

    # ---- 4) OHLCV candles -------------------------------------------------
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 200)
    if rates is not None and len(rates):
        print(f"  [4] CANDLES : {len(rates)} M1 bars, "
              f"last close={rates[-1]['close']}")
    else:
        print("  [4] CANDLES : none")

    mt5.shutdown()
    print("-" * 62)
    print("If sections [1]-[4] all show numbers, your MT5 data works.")
    print("The bot is ready:  python main.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
