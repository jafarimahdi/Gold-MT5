# Gold Trading System

An automated gold (XAUUSD) trading pipeline. **Step 2 (market analysis) is fully
implemented and tested.** Steps 1, 3, 4 and 5 are scaffolded with clean
interfaces, ready to be wired to live services.

## Pipeline

```
STEP 0  SETUP        config.py  (.env, keys, thresholds)
   |
STEP 1  DATA         step1_data_acquisition.py   Databento / Rithmic (demo fallback)
   |
STEP 2  ANALYSIS ⭐   step2_market_analysis.py    CVD · Delta · Footprint · Order Flow ·
   |                                             L2 Depth · L3 Events · ATR · BB ·
   |                                             ADX · MAs · MACD · RSI · Correlations ·
   |                                             VWAP · POC · Value Area · Economic
   |                                             Events · News Sentiment
   |
STEP 3  AI           step3_ai_decision.py        Gemini -> BUY/SELL/HOLD + confidence
   |
STEP 4  EXECUTION    step4_mt5_execution.py      MT5 (only if confidence > 70%)
   |
STEP 5  MONITORING   step5_monitoring.py         Track trades, loop back to Step 2
```

## Project layout

```
gold_trading_system/
├── .env.example                 # copy to .env and fill in your keys
├── main.py                      # entry point (runs the pipeline)
├── setup.py                     # library installation
├── config.py                    # settings & constants
├── requirements.txt
├── markets.py                   # market registry + symbol recognition
├── session.py                   # trading-session calendar (weekend detection)
├── risk_manager.py              # daily-loss / drawdown circuit breaker
├── spread_monitor.py            # futures <-> CFD basis monitor
├── backtest.py                  # replay history -> PnL/Sharpe/max-DD report
├── setup_markets.py             # interactive DATA/TRADE market selector
├── step1_data_acquisition.py    # thin wrapper (DataAcquisition)
├── data_providers.py            # demo / Rithmic / Databento / replay adapters
├── step2_market_analysis.py     # ⭐ ALL analysis tools (complete & tested)
├── step3_ai_decision.py         # Gemini AI integration
├── step4_mt5_execution.py       # Python execution + position management
├── step5_monitoring.py          # trade management & monitoring
├── mt5_signal_bridge.py         # writes the signal file the EA/indicator read
├── broker_diagnostic.py          # read-only broker/symbol/Level 2 diagnostic
├── test_python_execution.py      # safe Python open/close/reverse tests
├── PEPPERSTONE_SETUP.md          # Pepperstone MT5 setup and validation
├── CTRADER_NEXT.md               # cTrader investigation plan (not active yet)
├── mt5_ea/
│   ├── GoldTradingEA.mq5        # MT5 Expert Advisor (auto-trade from signal)
│   └── GoldSignalIndicator.mq5  # MT5 indicator (draws the signal)
├── paper_trade_checklist.md     # go-live checklist (follow this!)
├── demo_step2.py                # Step 2 unit tests (36 checks) + demo
├── test_data_providers.py      # provider->Step2 compatibility tests (29 checks)
├── test_markets.py              # market/symbol layer tests (28 checks)
├── test_indicators_golden.py    # indicator golden tests (19 checks)
├── test_session_risk.py         # weekend/no-data/risk resilience (25 checks)
├── test_key_rotation.py         # safe multi-key fallback (9 checks)
├── test_news.py                 # news caching/enrichment tests (11 checks)
├── test_python_execution.py     # Python execution/position tests (15 checks)
├── run_all_tests.py             # one command for all safe local tests
├── e2e_test.py                  # full pipeline integration tests
├── logs/                        # error/run logs
└── data/                        # outputs (snapshot, decisions, outcomes, ...)
```

## Status

| Step | Module | Status |
|------|--------|--------|
| 0 | `config.py` | ✅ Settings, broker/terminal path, execution mode and safety thresholds |
| 1 | `step1_data_acquisition.py` | ✅ MT5 provider; futures adapters retained; broker diagnostic included |
| 2 | `step2_market_analysis.py` | ✅ 25+ signals incl. technicals, order flow, news-time and macro data |
| 3 | `step3_ai_decision.py` | ✅ Gemini with modern SDK preferred, legacy fallback, immediate key failover |
| 4 | `step4_mt5_execution.py` | ✅ Python position management, broker volume/stops checks, EA routing |
| 5 | `step5_monitoring.py` | ✅ Monitoring, closed-deal IDs and continuous loop; live EA still requires Windows verification |

## Quick start (Windows)

Run from the directory containing `main.py`:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

# safe first run — no orders
# set TRADING_ENABLED=0 and EXECUTION_MODE=none in .env
python main.py

# read-only broker/symbol/Level 2 check
python broker_diagnostic.py
python mt5_test.py

# continuous loop
python main.py --loop

# backtest the signal engine on history
python backtest.py
```

Run the test suites:

```powershell
python demo_step2.py
python test_data_providers.py
python test_markets.py
python test_indicators_golden.py
python test_session_risk.py
python test_key_rotation.py
python test_news.py
python test_python_execution.py
python e2e_test.py
```

For a Pepperstone setup, read `PEPPERSTONE_SETUP.md` before changing broker settings.

## Safety nets (weekend / no-data / risk)

The bot refuses to trade when any of these trip (logged as `SAFETY: ...`):

1. **Session** — market closed (weekend / holiday / daily break).
2. **Feed** — Rithmic/Databento data stale or empty (heartbeat age > `STALE_DATA_SECONDS`).
3. **News** — inside the blackout window around high-impact events.
4. **Risk** — daily loss ≥ `DAILY_LOSS_LIMIT_PCT` % or drawdown ≥ `MAX_DRAWDOWN_PCT` %.
5. **Confidence** — AI confidence below the threshold.

Weekend testing without a live feed: record a session with `RECORD_DATA=1`,
then `DATA_SOURCE=replay` + `REPLAY_FILE=data/record_*.json` to replay it.
See `paper_trade_checklist.md` for the full go-live sequence.

## Two markets: futures DATA + CFD TRADE

The bot reads **L2/L3 order-book data from the futures market** (Rithmic/
Databento: GC = 100oz, MGC = 10oz) and **trades the CFD market on MT5**
(XAUUSD, GOLD, XAUUSD.i, ...). These are different instruments with slightly
different prices — so the analysis is **price-agnostic**:

- Signals are built from **movement** (returns, z-scores, deltas, CVD, OFI,
  ATR%) on the futures feed — never from absolute price levels.
- The CFD price is used **only at execution**: SL/TP are computed as
  **percentage offsets** from futures ATR and re-anchored to the live MT5 CFD
  price (both `step4_mt5_execution.py` and the MQL5 EA do this).
- Every snapshot tags its `data_market` and `trade_market` so nothing can mix.

**Pick both markets manually (easy switching):**

```bash
python3 setup_markets.py                    # interactive picker
python3 setup_markets.py --check            # verify current mapping
python3 setup_markets.py --data GC --trade XAUUSD   # one-liner
```

The wizard recognises common names (`GCZ4`, `GC.n.0`, `GC=F`, `MGC`, `XAUUSD.i`,
`GOLD`, `GOLDUSD`, `XAU/USD`...) and asks you to confirm manually that you are
receiving the right Rithmic data and that the correct CFD symbol is in MT5's
Market Watch. Your choices are written to `.env` (`DATA_SYMBOL`, `MT5_SYMBOL`).

## Choosing a data provider (STEP 1)

Edit one line in `.env`:

```ini
DATA_SOURCE=demo        # demo | rithmic | databento
```

| Provider | Credentials | What you get |
|----------|-------------|--------------|
| `demo` | none | synthetic data (test the whole pipeline now) |
| `rithmic` | `RITHMIC_USERNAME` / `RITHMIC_PASSWORD` | CME gold futures L2 depth + L3 order events |
| `databento` | `DATABENTO_API_KEY` | MBO (L3) + MBP-10 (L2) + trades |

**Changing credentials is a one-line `.env` edit + restart.** Rithmic demo
credentials rotate frequently — update `RITHMIC_USERNAME` / `RITHMIC_PASSWORD`
whenever Rithmic issues new ones (start with demo to validate, then swap in
live credentials). `config.reload_env()` re-reads `.env`, so the next connect
picks up new values.

> **Rithmic note:** Rithmic's R|API is C++/.NET — there is no official pip
> package. The mapping layer (`RithmicProvider.handle_depth / handle_order_event
> / handle_trade` and the Databento row mappers) is fully implemented and
> tested; you wire ONE transport into those callbacks. Options: a community
> Python wrapper (set `RITHMIC_LIB` to its module name), the R|Protocol socket
> API, or a bridge process. `test_data_providers.py` proves the mapped data
> flows through every Step-2 function.

> **Routing note:** Rithmic/Databento provide CME *futures* (GC = 100oz,
> MGC = 10oz). Spot XAUUSD has no central order book, so L2/L3 live on the
> futures market. The standard design is: analyse GC/MGC order flow and trade
> the ~1-correlated XAUUSD (or GC) on MT5.

## Trading on MT5 (indicator + auto-trading)

Two execution paths, both driven by the same analysis:

1. **Python SDK path** — Step 4 (`step4_mt5_execution.py`) sends orders through
   the `MetaTrader5` module (Windows + running MT5 terminal + bot login).
2. **EA path** — the pipeline writes a signal file (`mt5_signal_bridge.py`) that
   the MQL5 EA and indicator read from MT5's Common Files folder:

   1. In `.env`, set:
      `MT5_SIGNAL_FILE=C:\Users\<you>\AppData\Roaming\MetaQuotes\Terminal\Common\Files\gold_signal.txt`
      (find the exact path via MT5: *File → Open Data Folder*).
   2. Compile `mt5_ea/GoldTradingEA.mq5` and `mt5_ea/GoldSignalIndicator.mq5`
      in MetaEditor (F7).
   3. Attach the **indicator** to an XAUUSD chart to *see* BUY/SELL signals.
   4. Attach the **EA** to the chart and enable AutoTrading to trade them
      automatically (only when confidence ≥ 70% and not in news blackout).

The EA enforces the same rules as the Python side: min-confidence gate,
news-blackout block, ATR-based SL/TP, and it closes the opposite position
before reversing.

## What Step 2 produces

`analyze_market(market_data)` returns a `MarketSnapshot` containing:

- **Order flow** — CVD, delta, buy/sell pressure, L2 bid/ask depth, large orders,
  tick-rule side classification
- **Level 2 depth** — microprice, depth imbalance, liquidity slope/concentration,
  Order Flow Imbalance (OFI), absorption detection
- **Footprint** — buy/sell volume per price level, dominant level, strength, delta imbalance
- **Level 3 events** — order events, book reconstruction, event OFI, aggressor flow
  ratio, buy/sell streaks, icebergs, large orders, imbalance
- **Volatility** — ATR (+%), Bollinger Bands, volatility rank
- **Trend** — SMA 9/20/50, EMA 12/26, ADX/+DI/−DI, MACD, RSI, direction, strength
- **Volume profile** — VWAP, POC, value area, volume RoC, OBV, A/D, VWAP z-score bands
- **Macro** — DXY, 10Y yield, VIX, log-return correlations, real yields, risk sentiment
- **News & events** — headline sentiment, upcoming events, **news-time state
  (QUIET/WARNING/BLACKOUT)**
- **Signal** — composite strength, direction, confidence, **regime (TREND/RANGE)**,
  **CVD divergence**

The snapshot is saved as JSON to `data/market_snapshot.json` for Step 3, and each
pipeline pass is appended to `data/decisions_log.csv`.

### News-time behaviour

The bot refuses new entries during the blackout window around high-impact events
(FOMC/CPI/NFP), and during the warning window it widens stops and cuts size.
Windows are configurable in `.env` (`NEWS_*`). See `CHANGES.md` for details.

## Input schema for `analyze_market()`

See the docstring in `step1_data_acquisition.py` for the exact `market_data`
dict schema (tick_data, depths, order events, candles, macro, news).

## Notes

- **Sentiment** uses TextBlob blended with a financial-domain lexicon; it is
  asset-agnostic (e.g. "recession fears" reads negative even though that is
  bullish for gold). Tune `NewsAnalyzer._POSITIVE_WORDS` / `_NEGATIVE_WORDS`
  for gold-specific meaning.
- **Economic calendar** fetches a live feed when online; otherwise it falls
  back to a curated offline calendar so the pipeline never stalls.
- **MT5** (`MetaTrader5` SDK) is Windows-only and requires a running MT5
  terminal — everything else works cross-platform.
