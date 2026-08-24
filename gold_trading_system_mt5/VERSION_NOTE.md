# VERSION NOTE — this folder is the MT5-data version

There are TWO copies of the Gold Trading System:

1. `gold_trading_system/`      -> the **L3 (futures order-book) version**
   Uses Rithmic or Databento for full Level 2 + Level 3 data.

2. `gold_trading_system_mt5/`  -> **THIS folder (MT5 broker-data version)**
   Reads data from your own MetaTrader 5 terminal — FREE, no card, no vendor.

## What MT5 gives you (and what it doesn't)

| Data | MT5 | Notes |
|------|-----|-------|
| Price / bid / ask | ✅ | from your broker |
| Ticks with buy/sell side | ✅ | via tick flags (32=buy, 64=sell) |
| Level 2 depth | ✅ | broker's aggregated order book |
| OHLCV candles | ✅ | any timeframe |
| **Level 3 (order events)** | ❌ | brokers do NOT provide individual order events |

The Level 3 analyzer (order events, aggressor streaks, event OFI) therefore
stays empty in this version — it contributes nothing but does not break
anything. CVD, footprint, L2 OFI, microprice, technicals, macro, news and the
final signal all work fully from ticks + depth.

## How the two versions differ

The code is identical. The only difference is `DATA_SOURCE` in `.env`:

    this folder (.env):   DATA_SOURCE=mt5
    L3 folder  (.env):    DATA_SOURCE=databento   (or rithmic)

## Quick start (this version)

1. Install and open MetaTrader 5, log into a **demo** account, keep it open.
2. On Windows: `pip install MetaTrader5`
3. `python mt5_test.py`   -> verify you see TICK / LEVEL 2 / TICKS / CANDLES
4. `python main.py`       -> run the bot on MT5 data

## Switching back to L3 later

Just change `DATA_SOURCE` to `databento` or `rithmic` in `.env` — the rest of
the code is identical, so switching costs one line.
