# VERSION NOTE — MT5-data version (0.4.7)

This folder is the Pepperstone/MT5-ready foundation. The exact Pepperstone
symbol is detected locally; do not put broker credentials in Git.

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
| Level 2 depth | Depends on broker | Vantage test returned no book levels |
| OHLCV candles | ✅ | any timeframe |
| **Level 3 (order events)** | ❌ in MT5 | brokers do NOT provide individual order events |

The Level 3 analyzer stays empty for MT5 CFD data. If Level 2 is unavailable,
CVD and footprint values may be estimated from candle/tick volume and must be
labelled as estimated. True Level 2/Level 3 order flow is preserved through the
Rithmic/Databento futures providers.

## Execution modes

The current code supports one execution owner at a time:

    EXECUTION_MODE=none    analysis only; no actionable signal
    EXECUTION_MODE=python  Python opens/manages MT5 positions; EA is neutralised
    EXECUTION_MODE=ea      Python writes signals; only the MQL5 EA trades

New installations should use `TRADING_ENABLED=0` until the broker checks pass.

## How the two market-data versions differ

The same analysis and provider interfaces are retained, but the active source
is selected by `DATA_SOURCE` in `.env`:

    MT5 version:       DATA_SOURCE=mt5
    L3 futures path:   DATA_SOURCE=databento   (or rithmic)

One run currently uses one primary data source. Combining MT5 and futures feeds
requires a future data-fusion layer with timestamp and stale-feed handling.

## Quick start (this version)

1. Install and open MetaTrader 5, log into a **demo** account, keep it open.
2. Copy `.env.example` to `.env` and keep `TRADING_ENABLED=0`.
3. Set the exact broker symbol from Market Watch.
4. On Windows: `pip install -r requirements.txt`
5. `python broker_diagnostic.py` -> check symbol rules and Level 2.
6. `python mt5_test.py` -> verify TICK / LEVEL 2 / TICKS / CANDLES.
7. `python main.py` -> run one safe pass on MT5 data.
8. For Python execution, use `EXECUTION_MODE=python`; for the EA path use
   `EXECUTION_MODE=ea`. Never use both active at once.

## Switching to a futures data path later

Set `DATA_SOURCE=databento` or `DATA_SOURCE=rithmic`, configure the relevant
credentials locally, and keep the MT5 symbol for execution. Live provider
permissions and transports must be tested separately; changing one line alone
does not guarantee access.
