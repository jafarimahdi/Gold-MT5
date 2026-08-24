"""
backtest.py
===========
Backtest harness — replay history through the real Step-2 signal engine and
measure performance before risking real money.

Strategy (simple, transparent):
  - walk the candle series; at each bar run analyze_market() on the trailing
    window (the exact production code path),
  - if the composite signal is BUY/SELL with confidence >= threshold, open a
    position in that direction at the bar close (flat->long / flat->short),
  - exit on the opposite signal, or when SL/TP (ATR-based) is hit,
  - PnL is computed in price points; a small per-trade cost (spread) is applied.

Metrics reported: number of trades, win rate, total return %, profit factor,
Sharpe (per-bar, annualised x sqrt(252)), max drawdown %.

Usage:
    python3 backtest.py                # synthetic gold data
    python3 backtest.py --replay data/record_*.json   # recorded real data
    python3 backtest.py --confidence 60 --help
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np

import config
from step2_market_analysis import analyze_market


def _slice_candles(candles: Dict, end_idx: int) -> Dict:
    """Return the candle dict truncated to [0, end_idx)."""
    out = {}
    for k, v in candles.items():
        if v is None:
            out[k] = np.asarray([], dtype=float)
        else:
            out[k] = np.asarray(v)[:end_idx]
    return out


def run_backtest(candles: Dict[str, np.ndarray], confidence: float = 70.0,
                 sl_mult: Optional[float] = None, tp_mult: Optional[float] = None,
                 spread_points: float = 0.5, warmup: int = 60,
                 base_market: Optional[Dict] = None) -> Dict[str, Any]:
    """Replay history; return a metrics dict + trade list."""
    sl_mult = sl_mult if sl_mult is not None else config.STOP_LOSS_ATR_MULT
    tp_mult = tp_mult if tp_mult is not None else config.TAKE_PROFIT_ATR_MULT

    close = np.asarray(candles.get("close", []), dtype=float)
    high = np.asarray(candles.get("high", []), dtype=float)
    low = np.asarray(candles.get("low", []), dtype=float)
    open_ = np.asarray(candles.get("open", []), dtype=float)
    volume = np.asarray(candles.get("volume", []), dtype=float)

    n = len(close)
    if n < warmup + 5:
        return {"error": "not enough bars", "n": n, "trades": []}

    base = base_market or {}
    position = 0            # -1 short, 0 flat, +1 long
    entry_price = 0.0
    sl = tp = 0.0
    equity = 1000.0         # starting equity (arbitrary units)
    equity_curve: List[float] = [equity]
    peak = equity
    max_dd = 0.0
    trades: List[Dict] = []

    for i in range(warmup, n):
        bar_close = close[i]

        # manage open position: SL / TP check at bar extremes
        if position != 0:
            hit_sl = hit_tp = False
            if position > 0:
                if low[i] <= sl:
                    hit_sl = True
                elif high[i] >= tp:
                    hit_tp = True
            else:
                if high[i] >= sl:
                    hit_sl = True
                elif low[i] <= tp:
                    hit_tp = True
            if hit_sl or hit_tp:
                exit_px = sl if hit_sl else tp
                pnl = (exit_px - entry_price) * position - spread_points
                equity += pnl
                trades.append({"i": i, "side": "L" if position > 0 else "S",
                               "entry": round(entry_price, 2),
                               "exit": round(exit_px, 2),
                               "exit_reason": "SL" if hit_sl else "TP",
                               "pnl": round(pnl, 2)})
                position = 0
                bar_close = exit_px

        # build snapshot from trailing window and run the REAL analyzer
        window = _slice_candles(candles, i)
        market_data = dict(base)
        market_data["candles"] = window
        market_data["price"] = float(close[i])
        market_data["bid"] = float(close[i])
        market_data["ask"] = float(close[i])
        market_data.setdefault("news", {})["fetch_calendar"] = False
        try:
            snap = analyze_market(market_data)
        except Exception:
            continue

        signal = snap.signal_direction
        conf = snap.confidence
        atr = snap.volatility.atr

        # decide desired position
        desired = 0
        if conf >= confidence:
            desired = 1 if signal == "BUY" else (-1 if signal == "SELL" else 0)

        if desired != 0 and position == 0:
            # open
            position = desired
            entry_price = bar_close
            if atr > 0:
                if position > 0:
                    sl = entry_price - sl_mult * atr
                    tp = entry_price + tp_mult * atr
                else:
                    sl = entry_price + sl_mult * atr
                    tp = entry_price - tp_mult * atr
            else:
                sl = tp = entry_price

        elif desired != 0 and position != 0 and desired != position:
            # reverse: close then open
            pnl = (bar_close - entry_price) * position - spread_points
            equity += pnl
            trades.append({"i": i, "side": "L" if position > 0 else "S",
                           "entry": round(entry_price, 2),
                           "exit": round(bar_close, 2),
                           "exit_reason": "REVERSE", "pnl": round(pnl, 2)})
            position = desired
            entry_price = bar_close
            if atr > 0:
                sl = entry_price - (sl_mult * atr if desired > 0 else -sl_mult * atr)
                tp = entry_price + (tp_mult * atr if desired > 0 else -tp_mult * atr)
            else:
                sl = tp = entry_price

        # equity curve
        if position != 0:
            equity += (close[i] - close[i - 1]) * position
        equity_curve.append(equity)
        peak = max(peak, equity)
        dd = (peak - equity) / peak * 100.0 if peak > 0 else 0.0
        max_dd = max(max_dd, dd)

    # close any open position at the last close
    if position != 0:
        pnl = (close[-1] - entry_price) * position - spread_points
        equity += pnl
        trades.append({"i": n - 1, "side": "L" if position > 0 else "S",
                       "entry": round(entry_price, 2),
                       "exit": round(close[-1], 2),
                       "exit_reason": "EOD", "pnl": round(pnl, 2)})
        equity_curve[-1] = equity

    return _summarise(equity, equity_curve, max_dd, trades, close)


def _summarise(equity: float, curve: List[float], max_dd: float,
               trades: List[Dict], close: np.ndarray) -> Dict[str, Any]:
    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    gross_win = sum(t["pnl"] for t in wins)
    gross_loss = abs(sum(t["pnl"] for t in losses))

    rets = np.diff(np.asarray(curve, dtype=float)) / np.asarray(curve[:-1])
    sharpe = 0.0
    if len(rets) > 1 and rets.std() > 0:
        sharpe = float(rets.mean() / rets.std() * math.sqrt(252))

    return {
        "n_bars": int(len(close)),
        "n_trades": len(trades),
        "win_rate": round(100.0 * len(wins) / len(trades), 1) if trades else 0.0,
        "total_return_pct": round((equity / 1000.0 - 1.0) * 100.0, 2),
        "profit_factor": round(gross_win / gross_loss, 2) if gross_loss > 0 else None,
        "sharpe_annualized": round(sharpe, 3),
        "max_drawdown_pct": round(max_dd, 2),
        "avg_win": round(sum(t["pnl"] for t in wins) / len(wins), 2) if wins else 0.0,
        "avg_loss": round(sum(t["pnl"] for t in losses) / len(losses), 2) if losses else 0.0,
        "trades": trades,
    }


def load_candles(path: str) -> Dict[str, np.ndarray]:
    data = json.loads(open(path, encoding="utf-8").read())
    candles = data.get("candles", {})
    return {k: np.asarray(v, dtype=float) for k, v in candles.items() if v}


def print_report(report: Dict[str, Any]) -> None:
    print("=" * 62)
    print("BACKTEST REPORT")
    print("=" * 62)
    if "error" in report:
        print(f"  {report['error']}")
        return
    for k in ("n_bars", "n_trades", "win_rate", "total_return_pct",
              "profit_factor", "sharpe_annualized", "max_drawdown_pct",
              "avg_win", "avg_loss"):
        print(f"  {k:<20} {report.get(k)}")
    print("-" * 62)
    for t in report.get("trades", [])[:12]:
        print(f"  bar {t['i']:<4} {t['side']} entry {t['entry']:>9} -> "
              f"exit {t['exit']:>9} ({t['exit_reason']:<7}) pnl {t['pnl']:+8.2f}")
    if len(report.get("trades", [])) > 12:
        print(f"  ... {len(report['trades']) - 12} more trades")
    print("=" * 62)


def main() -> int:
    parser = argparse.ArgumentParser(description="Backtest the gold signal engine")
    parser.add_argument("--replay", help="path to a recorded market_data JSON")
    parser.add_argument("--confidence", type=float, default=70.0)
    parser.add_argument("--spread", type=float, default=0.5,
                        help="per-trade cost in price points")
    args = parser.parse_args()

    if args.replay:
        if args.replay.endswith(".npz"):
            # history_download.py output (compact NumPy archive)
            z = np.load(args.replay)
            candles = {k: z[k] for k in ("open", "high", "low", "close",
                                         "volume") if k in z.files}
            base = {}
        else:
            data = json.loads(open(args.replay, encoding="utf-8").read())
            candles = {k: np.asarray(v, dtype=float)
                       for k, v in data.get("candles", {}).items() if v}
            base = {k: v for k, v in data.items() if k != "candles"}
    else:
        from step2_market_analysis import _synthetic_market_data
        data = _synthetic_market_data()
        candles = data["candles"]
        base = {k: v for k, v in data.items() if k != "candles"}
    report = run_backtest(candles, confidence=args.confidence,
                          spread_points=args.spread, base_market=base)

    print_report(report)
    out = config.DATA_DIR / "backtest_report.json"
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"\nSaved -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
