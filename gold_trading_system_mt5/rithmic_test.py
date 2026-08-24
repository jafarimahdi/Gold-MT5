"""
rithmic_test.py
===============
Test your Rithmic connection BEFORE running the full bot.

Run:   python rithmic_test.py

It connects with your .env credentials, resolves the front-month GOLD contract
(GC on COMEX), streams trades + the order book (Level 2) for a few seconds and
prints what arrives.

If you see TICK / BOOK lines -> your Rithmic feed works.
If you see an error -> paste the WHOLE output back to me.

Prerequisites:
  - pip install async-rithmic
  - RITHMIC_USERNAME / RITHMIC_PASSWORD set in .env
  - Logged into R|Trader Pro once and accepted the market-data agreement;
    COMEX/CME market data enabled on your demo account.
"""

from __future__ import annotations

import asyncio
import sys
import traceback

import config

COLLECT_SECONDS = 15


def redact(text: str) -> str:
    """Hide the password if it ever appears in an error message."""
    pw = config.RITHMIC_PASSWORD
    if pw:
        return text.replace(pw, "***")
    return text


def _safe_error_text(exc: Exception) -> str:
    return redact(f"{type(exc).__name__}: {exc}")


def main() -> int:
    config.reload_env()

    print("=" * 62)
    print("RITHMIC CONNECTION TEST")
    print("=" * 62)
    print(f"  username      : {config.RITHMIC_USERNAME or '(empty)'}")
    print(f"  password      : {'***' if config.RITHMIC_PASSWORD else '(empty)'}")
    print(f"  system        : {config.RITHMIC_SYSTEM}")
    print(f"  app           : {config.RITHMIC_APP_NAME} {config.RITHMIC_APP_VERSION}")
    print(f"  gateway url   : {config.RITHMIC_URL}")
    print(f"  symbol/exch   : {config.RITHMIC_SYMBOL} / {config.RITHMIC_EXCHANGE}")
    print("-" * 62)

    if not config.RITHMIC_USERNAME or not config.RITHMIC_PASSWORD:
        print("ERROR: RITHMIC_USERNAME / RITHMIC_PASSWORD not set in .env")
        return 1

    try:
        from async_rithmic import RithmicClient, DataType, SysInfraType
    except ImportError as exc:
        print("ERROR: could not import async-rithmic.")
        print(f"  {exc}")
        print("Run:  pip install async-rithmic")
        return 1

    try:
        asyncio.run(_run(client=None))
    except KeyboardInterrupt:
        print("\nStopped.")
    except Exception as exc:
        print("\nUNEXPECTED ERROR (paste this whole block back to me):")
        traceback.print_exc()
        return 1
    return 0


async def _run(client=None):
    from async_rithmic import RithmicClient, DataType, SysInfraType

    client = RithmicClient(
        user=config.RITHMIC_USERNAME,
        password=config.RITHMIC_PASSWORD,
        system_name=config.RITHMIC_SYSTEM,
        app_name=config.RITHMIC_APP_NAME,
        app_version=config.RITHMIC_APP_VERSION,
        url=config.RITHMIC_URL,
    )

    counts = {"ticks": 0, "book": 0}

    def on_tick(data: dict):
        counts["ticks"] += 1
        if counts["ticks"] <= 5:
            print(f"  TICK  : price={data.get('trade_price')} "
                  f"size={data.get('trade_size')} "
                  f"aggressor={data.get('aggressor')}")

    def on_order_book(response):
        counts["book"] += 1
        if counts["book"] <= 8:
            nb = len(response.bid_price)
            na = len(response.ask_price)
            print(f"  BOOK  : update_type={response.update_type} "
                  f"bid_levels={nb} ask_levels={na}")
            if nb:
                print(f"          top bid {response.bid_price[0]} x {response.bid_size[0]}")
            if na:
                print(f"          top ask {response.ask_price[0]} x {response.ask_size[0]}")

    client.on_tick += on_tick
    client.on_order_book += on_order_book

    print("Connecting to Rithmic (ticker plant only) ...")
    try:
        await client.connect(plants=[SysInfraType.TICKER_PLANT])
    except Exception as exc:
        msg = str(exc)
        print(f"CONNECT FAILED: {redact(f'{type(exc).__name__}: {exc}')}")
        if "SYSTEM_NAME" in msg.upper() or "system name" in msg.lower():
            print("\n>>> The Rithmic server says the valid SYSTEM NAME is shown")
            print("    above in square brackets (e.g. ['Rithmic Test']).")
            print("    This usually means the SYSTEM NAME and the GATEWAY URL")
            print("    do not match. Fix BOTH in .env so they are consistent:")
            print("      RITHMIC_SYSTEM=Rithmic Paper Trading")
            print("      RITHMIC_URL=rprotocol.rithmic.com:443")
        elif "permission denied" in msg.lower() or "rpcode" in msg.lower():
            print("\n>>> Rithmic replied 'permission denied' (rpCode 13).")
            print("    Your settings are CORRECT (system + gateway + login all")
            print("    reached Rithmic). This is an ACCOUNT ENTITLEMENT issue:")
            print()
            print("    Rithmic's API (R|Protocol) is a SEPARATE service from")
            print("    R|Trader Pro. Your account works in R|Trader Pro, but")
            print("    API access must be enabled by Rithmic for your account")
            print("    (community reports: it is a paid add-on, and Rithmic")
            print("    assigns you an agreed app_name).")
            print()
            print("    What to do:")
            print("    1. Contact Rithmic support and ask:")
            print("       'Please enable R|Protocol API access for my paper")
            print("       trading account, including CME/COMEX market data.'")
            print("    2. Alternative: switch to Databento (free tier available,")
            print("       official Python SDK, MBO+MBP gold data). Your app")
            print("       already supports it: set DATA_SOURCE=databento and")
            print("       DATABENTO_API_KEY=... in .env")
            return
        else:
            print("\nCommon causes:")
            print("  1. Wrong username/password.")
            print("  2. Network/firewall blocking the gateway.")
        return
    print("Connected. Resolving front-month gold contract ...")

    symbol = config.RITHMIC_SYMBOL
    exchange = config.RITHMIC_EXCHANGE
    try:
        security_code = await client.get_front_month_contract(symbol, exchange)
    except Exception as exc:
        print(f"CONTRACT LOOKUP FAILED: {type(exc).__name__}: {exc}")
        return
    print(f"Gold contract: {security_code} ({symbol} / {exchange})")

    print(f"Subscribing to trades + order book for {COLLECT_SECONDS}s ...")
    print("(if the market is open you should see TICK/BOOK lines below)")
    print()

    data_type = int(DataType.LAST_TRADE) | int(DataType.ORDER_BOOK)  # 5
    await client.subscribe_to_market_data(security_code, exchange, data_type)

    await asyncio.sleep(COLLECT_SECONDS)

    print()
    print("-" * 62)
    print(f"  ticks received  : {counts['ticks']}")
    print(f"  book updates    : {counts['book']}")
    print("-" * 62)
    if counts["ticks"] == 0 and counts["book"] == 0:
        print("No data arrived. Possible reasons:")
        print("  1. The market is closed (weekend / outside CME hours).")
        print("  2. COMEX market data is not enabled on your account.")
        print("  3. Wrong gateway url (should be rprotocol.rithmic.com:443).")
    else:
        print("SUCCESS — your Rithmic feed is working.")

    await client.disconnect()


if __name__ == "__main__":
    sys.exit(main())
