"""
broker_diagnostic.py
====================
Read-only MT5 broker/terminal diagnostic.

This script does not send orders. It identifies the configured symbol (or
nearby gold symbols), checks the terminal connection, reports broker trading
constraints, and tests whether market-book/Level 2 data is available.

Run from the application directory:
    python broker_diagnostic.py

The result is also saved to data/broker_diagnostic.json (ignored runtime data).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import config


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return str(value)


def _symbol_dict(info: Any, tick: Any, book: Any) -> Dict[str, Any]:
    return {
        "name": getattr(info, "name", ""),
        "visible": bool(getattr(info, "visible", False)),
        "select": bool(getattr(info, "select", False)),
        "trade_mode": getattr(info, "trade_mode", None),
        "digits": getattr(info, "digits", None),
        "point": getattr(info, "point", None),
        "volume_min": getattr(info, "volume_min", None),
        "volume_max": getattr(info, "volume_max", None),
        "volume_step": getattr(info, "volume_step", None),
        "trade_stops_level": getattr(info, "trade_stops_level", None),
        "trade_freeze_level": getattr(info, "trade_freeze_level", None),
        "filling_mode": getattr(info, "filling_mode", None),
        "bid": getattr(tick, "bid", None) if tick else None,
        "ask": getattr(tick, "ask", None) if tick else None,
        "last": getattr(tick, "last", None) if tick else None,
        "book_levels": len(book or []),
    }


def _candidate_names(mt5: Any, target: str) -> List[str]:
    names = [target]
    try:
        all_symbols = mt5.symbols_get() or []
        for info in all_symbols:
            name = str(getattr(info, "name", ""))
            upper = name.upper()
            if ("XAU" in upper or "GOLD" in upper) and name not in names:
                names.append(name)
    except Exception:
        pass
    return names


def main() -> int:
    config.reload_env()
    try:
        import MetaTrader5 as mt5
    except ImportError:
        print("ERROR: MetaTrader5 package is not installed.")
        return 1

    print("=" * 70)
    print("MT5 BROKER DIAGNOSTIC (READ ONLY)")
    print("=" * 70)
    print(f"Broker label      : {config.BROKER_NAME or '(not configured)'}")
    print(f"Configured symbol : {config.MT5_SYMBOL}")
    print(f"Terminal path     : {config.MT5_TERMINAL_PATH or '(running/default terminal)'}")
    print("No orders will be sent by this program.")
    print("-" * 70)

    init_kwargs: Dict[str, Any] = {}
    if config.MT5_TERMINAL_PATH:
        init_kwargs["path"] = config.MT5_TERMINAL_PATH
    if config.MT5_LOGIN:
        init_kwargs.update(login=config.MT5_LOGIN,
                           password=config.MT5_PASSWORD,
                           server=config.MT5_SERVER)

    if not mt5.initialize(**init_kwargs):
        print(f"ERROR: MT5 initialize failed: {mt5.last_error()}")
        return 1

    result: Dict[str, Any] = {"broker": config.BROKER_NAME,
                              "configured_symbol": config.MT5_SYMBOL,
                              "symbols": []}
    try:
        terminal = mt5.terminal_info()
        account = mt5.account_info()
        print(f"Terminal connected : {terminal is not None}")
        print(f"Actual terminal   : {getattr(terminal, 'path', '') or '(not reported)'}")
        print(f"Broker/company    : {getattr(account, 'company', '') or '(not reported)'}")
        print(f"Account server    : {getattr(account, 'server', '') or '(not reported)'}")
        names = _candidate_names(mt5, config.MT5_SYMBOL)
        print(f"Gold candidates     : {', '.join(names) if names else '(none)'}")

        selected_any = False
        for name in names:
            try:
                selected = bool(mt5.symbol_select(name, True))
                info = mt5.symbol_info(name)
                tick = mt5.symbol_info_tick(name)
                book = []
                if selected:
                    try:
                        mt5.market_book_add(name)
                        time.sleep(0.5)
                        book = mt5.market_book_get(name) or []
                    finally:
                        try:
                            mt5.market_book_release(name)
                        except Exception:
                            pass
                if info is None:
                    print(f"{name}: not found")
                    continue
                selected_any = selected_any or selected
                item = _symbol_dict(info, tick, book)
                item["selected_now"] = selected
                result["symbols"].append(item)
                print(f"\n{name}")
                print(f"  selected          : {selected}")
                print(f"  bid / ask         : {item['bid']} / {item['ask']}")
                print(f"  digits / point    : {item['digits']} / {item['point']}")
                print(f"  volume min/step/max: {item['volume_min']} / "
                      f"{item['volume_step']} / {item['volume_max']}")
                print(f"  stops/freeze level : {item['trade_stops_level']} / "
                      f"{item['trade_freeze_level']}")
                print(f"  filling mode      : {item['filling_mode']}")
                print(f"  Level 2 levels    : {item['book_levels']}")
            except Exception as exc:
                print(f"{name}: diagnostic failed ({type(exc).__name__}: {exc})")

        result["selected_any"] = selected_any
        result["level2_available"] = any(
            int(item.get("book_levels") or 0) > 0
            for item in result["symbols"]
        )
        out = config.DATA_DIR / "broker_diagnostic.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(_json_safe(result), indent=2), encoding="utf-8")
        print("\n" + "-" * 70)
        print(f"Saved diagnostic -> {out}")
        print(f"Level 2 available : {result['level2_available']}")
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    sys.exit(main())
