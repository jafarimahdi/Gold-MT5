"""
history_download.py
===================
Download PAST gold candles from your MT5 terminal for backtesting / training.

This is how you build your own history archive (e.g. the last 6 months), so
you can later run the robot over old data and measure whether it would have
made money — the same way professional traders test a strategy before using
it with real money.

Files are saved as compact `.npz` (NumPy compressed) — small, and they load
almost instantly. One file per timeframe.

Usage (run from Git Bash, with MT5 running + logged in):
    python history_download.py                    # 6 months, M1 + M5 + M15 + H1
    python history_download.py --months 12 --tf M1
    python history_download.py --symbol XAUUSD+ --months 3 --tf M1,M5

After downloading, backtest with:
    python backtest.py --replay data/history_XAUUSD__M1.npz
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone

import numpy as np

import config


def main() -> int:
    parser = argparse.ArgumentParser(description="Download MT5 gold history")
    parser.add_argument("--symbol", default="",
                        help="MT5 symbol (default: MT5_SYMBOL from .env)")
    parser.add_argument("--months", type=int, default=6,
                        help="how many months back to download")
    parser.add_argument("--tf", default="M1,M5,M15,H1",
                        help="timeframes, comma-separated")
    args = parser.parse_args()

    try:
        import MetaTrader5 as mt5
    except ImportError:
        print("ERROR: 'MetaTrader5' is not installed (Windows only).")
        return 1

    symbol = args.symbol or config.MT5_SYMBOL
    tfs = [t.strip().upper() for t in args.tf.split(",") if t.strip()]
    tf_map = {"M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5,
              "M15": mt5.TIMEFRAME_M15, "M30": mt5.TIMEFRAME_M30,
              "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
              "D1": mt5.TIMEFRAME_D1}

    if not config.mt5_initialize(mt5):
        print(f"ERROR: cannot connect to MT5: {mt5.last_error()}")
        print("       Is the MT5 terminal running and logged in?")
        return 1
    mt5.symbol_select(symbol, True)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    start = now - timedelta(days=args.months * 30)
    print(f"Downloading {args.months} months of {symbol} from MT5 ...")

    for tf in tfs:
        mttf = tf_map.get(tf)
        if mttf is None:
            print(f"  skip unknown timeframe '{tf}'")
            continue

        chunks = []
        cur = start
        while cur < now:
            end = min(cur + timedelta(days=31), now)
            try:
                rates = mt5.copy_rates_range(symbol, mttf, cur, end)
            except Exception as exc:
                print(f"  {tf}: copy failed ({exc})")
                rates = None
            if rates is not None and len(rates):
                chunks.append(rates)
            cur = end

        if not chunks:
            print(f"  {tf}: no data downloaded (is {symbol} in Market Watch?)")
            continue

        allr = np.concatenate(chunks)
        order = np.argsort(allr["time"])
        allr = allr[order]
        _, idx = np.unique(allr["time"], return_index=True)
        allr = allr[np.sort(idx)]

        vol = np.asarray([r["real_volume"] if r["real_volume"] else
                          r["tick_volume"] for r in allr], dtype=float)
        safe = symbol.replace("+", "_").replace(".", "_")
        out = config.DATA_DIR / f"history_{safe}_{tf}.npz"
        np.savez_compressed(out,
                            time=allr["time"],
                            open=allr["open"],
                            high=allr["high"],
                            low=allr["low"],
                            close=allr["close"],
                            volume=vol)
        print(f"  {tf}: {len(allr)} bars -> {out} "
              f"({out.stat().st_size / 1024:.0f} KB)")

    mt5.shutdown()
    print("\nDone. Backtest with:")
    print(f"  python backtest.py --replay data/history_{symbol.replace('+','_').replace('.','_')}_M1.npz")
    return 0


if __name__ == "__main__":
    sys.exit(main())
