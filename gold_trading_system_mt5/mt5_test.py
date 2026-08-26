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
import time
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

    init_kwargs = {}
    if config.MT5_TERMINAL_PATH:
        init_kwargs["path"] = config.MT5_TERMINAL_PATH
    if config.MT5_LOGIN:
        init_kwargs.update(login=config.MT5_LOGIN,
                           password=config.MT5_PASSWORD,
                           server=config.MT5_SERVER)
    ok = mt5.initialize(**init_kwargs)
    if not ok:
        print(f"ERROR: mt5.initialize() failed: {mt5.last_error()}")
        print("  Make sure the Pepperstone MT5 terminal is RUNNING and logged")
        print("  into an account (demo is fine).")
        return 1

    terminal = mt5.terminal_info()
    account = mt5.account_info()
    actual_path = getattr(terminal, "path", "") if terminal else ""
    actual_company = getattr(account, "company", "") if account else ""
    actual_server = getattr(account, "server", "") if account else ""
    print(f"  connected path: {actual_path or '(not reported)'}")
    print(f"  broker/company : {actual_company or '(not reported)'}")
    print(f"  account server: {actual_server or '(not reported)'}")

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
        added = mt5.market_book_add(symbol)
        book = None
        # Market-book subscription can take a short time to populate. Retry
        # read-only several times before declaring that Level 2 is empty.
        if added:
            for _ in range(6):
                book = mt5.market_book_get(symbol)
                if book:
                    break
                time.sleep(0.5)
        if book:
            print(f"  [2] LEVEL 2 : {len(book)} depth entries (first 5 shown):")
            for e in book[:5]:
                entry_type = int(e.type)
                buy_type = int(getattr(mt5, "BOOK_TYPE_BUY", 2))
                sell_type = int(getattr(mt5, "BOOK_TYPE_SELL", 1))
                if entry_type == buy_type or (entry_type == 0 and buy_type != 0):
                    side = "BID"
                elif entry_type == sell_type:
                    side = "ASK"
                else:
                    side = f"TYPE_{entry_type}"
                print(f"          {side}  {e.price} x {e.volume}")
        elif not added:
            print(f"  [2] LEVEL 2 : subscription failed ({mt5.last_error()})")
        else:
            print("  [2] LEVEL 2 : empty after 3 seconds — broker may not publish depth")
        mt5.market_book_release(symbol) if added else None
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
