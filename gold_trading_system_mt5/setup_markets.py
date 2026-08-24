"""
setup_markets.py
================
Interactive market selector for the gold trading system.

The bot reads data from ONE market (futures feed: GC / MGC ...) and trades on
ANOTHER (MT5 CFD: XAUUSD / GOLD ...). This wizard lets you choose both sides
manually and confirm you are receiving the right data — no code edits needed;
your choices are written straight into `.env`.

Usage
-----
    python3 setup_markets.py                  # interactive picker
    python3 setup_markets.py --check          # verify current mapping (no prompts)
    python3 setup_markets.py --data GC --trade XAUUSD   # set non-interactively

The pipeline is price-agnostic: it analyses market MOVEMENT (returns, z-scores,
deltas, ATR%) on the futures feed and only uses the CFD price at execution, so
futures and CFD prices never need to match.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import config
from markets import (MARKETS, MarketProfile, list_markets, normalize_symbol,
                     resolve_market)


# --------------------------------------------------------------------------- #
# .env editing
# --------------------------------------------------------------------------- #

def env_path() -> Path:
    return config.BASE_DIR / ".env"


def update_env(updates: Dict[str, str]) -> None:
    """Set keys in .env (create the file if missing), preserving everything else."""
    path = env_path()
    lines: List[str] = []
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()

    applied = {k: False for k in updates}
    out: List[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in updates:
                out.append(f"{key}={updates[key]}")
                applied[key] = True
                continue
        out.append(line)
    for key, value in updates.items():
        if not applied[key]:
            out.append(f"{key}={value}")

    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"Updated {path}")


# --------------------------------------------------------------------------- #
# Display / selection helpers
# --------------------------------------------------------------------------- #

def print_market_table() -> None:
    print("\nRecognised gold markets:")
    print(f"  {'id':<8} {'kind':<9} {'label'}")
    print("  " + "-" * 60)
    for prof in list_markets():
        print(f"  {prof.id:<8} {prof.kind:<9} {prof.label}")
        print(f"  {'':<8} {'':<9} venue: {prof.venue}")


def show_symbol_recognition() -> None:
    """Demonstrate that vendor/broker symbol names are auto-recognised."""
    samples = ["GC", "GCZ4", "GC.n.0", "GC=F", "MGC", "MGCZ24",
               "XAUUSD", "XAUUSD.i", "XAUUSD.m", "GOLD", "GOLDUSD", "XAU/USD"]
    print("\nSymbol recognition (examples):")
    for s in samples:
        pid = normalize_symbol(s)
        print(f"  {s:<12} -> {pid}")


def pick_market(role: str, default: str) -> str:
    """Interactively pick a market; returns the raw symbol string."""
    print_market_table()
    show_symbol_recognition()
    prompt = (f"\nEnter the {'DATA (futures feed)' if role == 'data' else 'TRADE (MT5 CFD)'} "
              f"symbol [{default}]: ")
    raw = input(prompt).strip() or default
    prof, notes = resolve_market(raw, role)
    for n in notes:
        print(f"  note: {n}")
    print(f"  -> resolved to {prof.id}: {prof.label} ({prof.kind}, {prof.venue})")
    return raw


def confirm(prompt: str) -> bool:
    ans = input(prompt + " [y/N]: ").strip().lower()
    return ans in ("y", "yes")


# --------------------------------------------------------------------------- #
# Verification (--check)
# --------------------------------------------------------------------------- #

def check_mapping() -> int:
    print("=" * 64)
    print("MARKET MAPPING CHECK")
    print("=" * 64)

    data_symbol = config.DATA_SYMBOL
    trade_symbol = config.MT5_SYMBOL

    print(f"  DATA source        : {config.DATA_SOURCE}")
    print(f"  DATA symbol (feed) : {data_symbol}")
    print(f"  TRADE symbol (MT5) : {trade_symbol}")
    print()

    problems = 0
    try:
        dprof, dnotes = resolve_market(data_symbol, "data")
        print(f"  DATA  '{data_symbol}' -> {dprof.id} ({dprof.label})")
        for n in dnotes:
            print(f"         note: {n}")
            problems += 1
    except ValueError as exc:
        print(f"  DATA  ERROR: {exc}")
        problems += 1

    try:
        tprof, tnotes = resolve_market(trade_symbol, "trade")
        print(f"  TRADE '{trade_symbol}' -> {tprof.id} ({tprof.label})")
        for n in tnotes:
            print(f"         note: {n}")
    except ValueError as exc:
        print(f"  TRADE ERROR: {exc}")
        problems += 1

    # sanity: are these the same instrument class?
    try:
        dpid = normalize_symbol(data_symbol)
        tpid = normalize_symbol(trade_symbol)
        if dpid == tpid:
            print(f"\n  WARNING: data and trade markets are the same ({dpid}).")
            print("           That is fine if your feed and broker both use the")
            print("           same market; otherwise check your .env settings.")
    except Exception:
        pass

    show_symbol_recognition()

    print("-" * 64)
    if problems:
        print(f"RESULT: {problems} problem(s) to review. Run "
              f"'python3 setup_markets.py' to fix.")
        return 1
    print("RESULT: mapping OK. Analysis is price-agnostic: futures feed ->")
    print("        relative signals -> CFD execution. Prices never mix.")
    return 0


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main() -> int:
    parser = argparse.ArgumentParser(description="Select data & trade markets")
    parser.add_argument("--check", action="store_true",
                        help="verify the current mapping without prompts")
    parser.add_argument("--data", help="set the DATA (futures) symbol, e.g. GC")
    parser.add_argument("--trade", help="set the TRADE (MT5 CFD) symbol, e.g. XAUUSD")
    args = parser.parse_args()

    if args.check:
        return check_mapping()

    if args.data and args.trade:
        # non-interactive set
        dprof, _ = resolve_market(args.data, "data")
        tprof, _ = resolve_market(args.trade, "trade")
        update_env({
            "DATA_SYMBOL": args.data,
            "MT5_SYMBOL": args.trade,
            "TRADING_SYMBOL": args.trade,
            "DATA_MARKET": dprof.id,
            "TRADE_MARKET": tprof.id,
        })
        config.reload_env()
        print(f"Set DATA={dprof.id} ({args.data}), TRADE={tprof.id} ({args.trade}).")
        return 0

    # interactive
    print("=" * 64)
    print("GOLD TRADING SYSTEM — MARKET SETUP")
    print("=" * 64)
    print("You will pick TWO markets:")
    print("  1. DATA market  — where L2/L3 order-book data comes from")
    print("                    (Rithmic/Databento futures: GC, MGC, ...)")
    print("  2. TRADE market — the market you trade on MT5 (CFD: XAUUSD, GOLD...)")
    print()
    print("Prices differ between futures and CFD; that is fine — the bot")
    print("analyses MOVEMENT (returns, deltas, ATR%) and only uses the CFD")
    print("price at execution time.")

    data_sym = pick_market("data", config.DATA_SYMBOL)
    trade_sym = pick_market("trade", config.MT5_SYMBOL)

    dprof, _ = resolve_market(data_sym, "data")
    tprof, _ = resolve_market(trade_sym, "trade")

    print("\nSummary of your choice:")
    print(f"  DATA  : {dprof.id} ({dprof.label})  <- feed symbol '{data_sym}'")
    print(f"  TRADE : {tprof.id} ({tprof.label})  <- MT5 symbol '{trade_sym}'")
    print()

    # manual confirmation that the Rithmic feed is correct
    print("Before you continue, please verify manually that:")
    print("  1. Your Rithmic/Databento terminal is showing GOLD data for the")
    print("     DATA market above (order book moving, correct contract).")
    print("  2. Your MT5 terminal has the TRADE symbol above in the Market Watch")
    print("     (the CFD market your broker offers).")
    if not confirm("Is everything correct?"):
        print("Aborted — nothing was changed.")
        return 1

    update_env({
        "DATA_SYMBOL": data_sym,
        "MT5_SYMBOL": trade_sym,
        "TRADING_SYMBOL": trade_sym,
        "DATA_MARKET": dprof.id,
        "TRADE_MARKET": tprof.id,
    })
    config.reload_env()
    print("\nDone. Settings written to .env:")
    print(f"  DATA_SYMBOL={data_sym}   MT5_SYMBOL={trade_sym}")
    print("Restart the pipeline (or run --check) to confirm.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
