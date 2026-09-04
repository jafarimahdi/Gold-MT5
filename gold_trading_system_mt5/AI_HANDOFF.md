# Gold Trading System — AI Handoff and Backup Information

**Purpose:** This file is the durable project handoff for future development. Any new developer or AI assistant should read this file before changing the application.

**Last updated:** 2026-08-27  
**Current version:** 0.6.7 — final reporting, risk, EA and test-isolation package  
**Repository:** https://github.com/jafarimahdi/Gold-MT5  
**Branch reviewed:** `main`  
**Base commit reviewed:** `5e718a3` (`upload app`)  
**0.6.7 status:** implemented and fully validated in the development workspace; final ZIP prepared after package-content check  
**Application directory:** `gold_trading_system_mt5/`

> Keep this file inside the application folder and update it after every meaningful version improvement. Never put real API keys, passwords, tokens, private certificates, or the real `.env` file in this document.

---

## 1. Project summary

This project is a Python-based automated gold-trading system for MetaTrader 5. It is designed to work with the broker's gold symbol, currently:

```text
XAUUSD
```

The application can:

1. Read market data from a running MetaTrader 5 terminal.
2. Analyse price, candles, ticks, Level 2 market-book data, technical indicators, news and macro information.
3. Build a composite market signal.
4. Ask Gemini AI to return `BUY`, `SELL`, or `HOLD` with a confidence percentage.
5. Apply market-session, data-quality, news, spread, risk and anti-overtrading safety gates.
6. Send an order directly through the Python MetaTrader5 package, or write a signal file for an MQL5 Expert Advisor.
7. Monitor open positions and maintain decision, trade and system logs.
8. Record market data for later replay and backtesting.

This is a trading automation framework. It has not yet proved that the strategy is profitable on real market data. It must be operated on a demo account until real-data testing and paper trading demonstrate positive expectancy.

---

## 2. Application pipeline

```text
STEP 0  CONFIGURATION
        .env, symbols, credentials, thresholds
             |
STEP 1  DATA ACQUISITION
        MT5 / demo / replay / Rithmic / Databento
             |
STEP 2  MARKET ANALYSIS
        technicals, order flow, Level 2, volatility, news, macro
             |
STEP 3  AI DECISION
        Gemini -> BUY / SELL / HOLD + confidence
             |
SAFETY  session, stale data, spread, news, risk and trade limits
             |
STEP 4  EXECUTION
        Python MT5 SDK and/or MQL5 EA signal bridge
             |
STEP 5  MONITORING
        open positions, closed deals, logs and continuous loop
```

The normal entry point is:

```text
main.py
```

One pass:

```powershell
python main.py
```

Continuous operation:

```powershell
python main.py --loop
```

The loop interval is controlled by `MONITOR_POLL_SECONDS`, whose default is 60 seconds.

---

## 3. Important files

### Core application

| File | Purpose |
|---|---|
| `main.py` | Orchestrates the full pipeline and safety gates |
| `config.py` | Loads `.env` and exposes all configuration values |
| `data_providers.py` | MT5, demo, replay, Rithmic and Databento providers |
| `step1_data_acquisition.py` | Stable interface to the provider layer |
| `step2_market_analysis.py` | Main analysis engine and `MarketSnapshot` |
| `step3_ai_decision.py` | Gemini integration and response parsing |
| `step4_mt5_execution.py` | Direct Python-based MT5 execution |
| `step5_monitoring.py` | Position checks and continuous loop |
| `mt5_signal_bridge.py` | Writes the signal consumed by the MQL5 EA/indicator |
| `risk_manager.py` | Daily-loss and drawdown circuit breaker |
| `trade_guard.py` | Cooldown and maximum-trades-per-day protection |
| `session.py` | Weekday, weekend and daily-break checks |
| `markets.py` | Symbol normalization and market identity |
| `news.py` | News headlines and economic calendar enrichment |
| `macro.py` | DXY, yield and VIX data enrichment |
| `backtest.py` | Replay/backtest harness |
| `maintenance.py` | Cleanup and log/data retention |

### MT5 files

```text
mt5_ea/GoldTradingEA.mq5
mt5_ea/GoldSignalIndicator.mq5
```

The EA reads `gold_signal.txt`, validates the direction/confidence/news state, and can open, close, reverse and trail positions. The indicator displays the signal on the MT5 chart.

### Tests

```text
demo_step2.py
test_data_providers.py
test_markets.py
test_indicators_golden.py
test_session_risk.py
test_key_rotation.py
test_news.py
e2e_test.py
```

`e2e_test.py` uses mocked Gemini and mocked MetaTrader5 modules. It does not prove that the real terminal or broker will accept orders.

---

## 4. Intended current runtime configuration

The owner's local `.env` was supplied without secrets. The intended current Pepperstone configuration is:

```env
DATA_SOURCE=mt5
MT5_SYMBOL=XAUUSD
TRADING_SYMBOL=XAUUSD
DATA_SYMBOL=XAUUSD
DATA_MARKET=XAUUSD
TRADE_MARKET=XAUUSD
MT5_LOGIN=0
EXECUTION_MODE=python
TRADING_ENABLED=0
```

### Meaning of the symbol settings

- `XAUUSD` is the exact Pepperstone symbol used by MT5.
- The application may normalize equivalent market names internally, but MT5 communication must use the exact configured symbol.
- Confirm the exact symbol in MT5 Market Watch before running the bot.

`MT5_LOGIN=0` means the program connects to the already-open and logged-in MT5 terminal. It does not need the MT5 password or server in that mode.

### AI settings

```env
GEMINI_API_KEY=
GEMINI_API_KEY_2=
GEMINI_API_KEY_3=
GEMINI_MODEL=gemini-3.7-flash
GEMINI_MODELS=gemini-3.7-flash,gemini-3.5-flash,gemini-3.6-flash,gemini-2.5-flash
AI_MIN_SIGNAL_STRENGTH=8
AI_MIN_INTERVAL_MINUTES=1
AI_MAX_CALLS_PER_DAY=2000
```

Without a Gemini key, Step 3 returns `HOLD` and should not trade. Gemini package installation may be required because `google-generativeai` is optional/commented in the current `requirements.txt`.

An AI call every minute can approach the daily free-tier quota. Monitor rate limits and reduce the frequency if necessary.

### Safety and filters

```env
TRADING_ENABLED=1
CONFIRM_ENABLED=1
CONFIRM_TIMEFRAMES=H1,M15,M5
MAX_SPREAD_PCT=0.05
ORDER_BLOCKS_ENABLED=1
COOLDOWN_MINUTES=15
MAX_TRADES_PER_DAY=30
```

For all installation, connection and observation testing, use:

```env
TRADING_ENABLED=0
```

Do not change it to `1` until the MT5 demo connection, signal file, EA and execution design have been checked.

### News and macro

```env
NEWS_ENABLED=1
NEWS_CACHE_MINUTES=15
NEWS_MAX_HEADLINES=20
NEWS_TIMEOUT=8

MACRO_ENABLED=1
MACRO_CACHE_MINUTES=15
MACRO_TIMEOUT=8
```

News controls:

```env
NEWS_WARNING_MINUTES=30
NEWS_BLACKOUT_BEFORE_MINUTES=15
NEWS_BLACKOUT_AFTER_MINUTES=20
NEWS_WIDEN_STOP_MULT=1.5
NEWS_REDUCE_SIZE_PCT=0.5
```

### Defaults inherited from `config.py`

The supplied `.env` does not define these values, so the code defaults apply:

```env
TIMEFRAME=M1
RISK_PER_TRADE_PCT=1.0
STOP_LOSS_ATR_MULT=1.5
TAKE_PROFIT_ATR_MULT=3.0
LOT_SIZE=0.1
CONTRACT_SIZE=100
ACCOUNT_EQUITY=10000
MAX_LOT_SIZE=1.0
STALE_DATA_SECONDS=300
DAILY_LOSS_LIMIT_PCT=3.0
MAX_DRAWDOWN_PCT=10.0
MONITOR_POLL_SECONDS=60
```

### Signal-file path

The local configuration points Python to an individual MT5 terminal folder similar to:

```text
C:\Users\<username>\AppData\Roaming\MetaQuotes\Terminal\<terminal-id>\MQL5\Files\gold_signal.txt
```

The exact path must be confirmed in MT5 using:

```text
File -> Open Data Folder
```

The EA and indicator use the filename `gold_signal.txt` and try both the Common Files folder and the terminal-specific `MQL5\Files` folder. Python and MT5 must refer to the same terminal installation.

---

## 5. Analysis details

`step2_market_analysis.py` creates a `MarketSnapshot` containing:

- CVD, delta and buying/selling pressure;
- Level 2 bid/ask depth and imbalance;
- microprice, liquidity slope, OFI and absorption;
- footprint volume by price level;
- Level 3 event metrics when a true Level 3 provider is used;
- ATR, Bollinger Bands, volatility rank;
- SMA, EMA, ADX, MACD and RSI;
- VWAP, POC, value area and volume statistics;
- DXY, US 10-year yield and VIX metrics;
- headline sentiment and scheduled economic events;
- trend/range regime;
- CVD divergence;
- support, resistance and order-block zones;
- composite direction, strength and confidence.

The snapshot is saved to:

```text
data/market_snapshot.json
```

The decision journal is saved to:

```text
data/decisions_log.csv
```

The application also creates trade outcomes and state files under `data/`.
These are generated runtime files and should normally be ignored by Git, except for deliberately selected sample/replay data.

---

## 6. Critical execution design issue

The current `main.py` performs the Python execution step and also writes the EA signal file during the same pipeline pass.

Therefore, it is possible to accidentally enable both:

1. direct Python MT5 order execution; and
2. the MQL5 EA with AutoTrading enabled.

This could result in duplicate or conflicting orders.

Before enabling trading, the project should add an explicit execution mode, for example:

```env
EXECUTION_MODE=none
```

Allowed values should be:

```text
none
python
ea
```

Recommended behavior:

- `none`: analysis and signal generation only;
- `python`: direct Python MT5 execution only;
- `ea`: signal-file generation only, with the EA responsible for execution.

Until this is implemented and tested, keep `TRADING_ENABLED=0`.

The EA also uses its own `InpManualLots` value, while the Python path calculates risk-based lots. These two position-sizing approaches are not currently unified.

---

## 7. Validation already performed

The public repository was downloaded and tested in a Linux sandbox using Python 3.13. The core scientific dependencies available there included NumPy, pandas, requests and TextBlob. Real `MetaTrader5`, Gemini and Rithmic connectivity were not available.

### Passed

```text
Python compilation                  PASS
demo_step2.py                       36/36
test_data_providers.py             27/27
test_indicators_golden.py          19/19
test_session_risk.py               25/25
test_key_rotation.py                6/6
test_news.py                        11/11
safe demo execution of main.py     PASS
```

The safe demo run completed:

```text
STEP 1  DATA ACQUISITION     OK
STEP 2  MARKET ANALYSIS      OK
STEP 3  AI DECISION          HOLD
STEP 4  EXECUTION            SKIPPED
STEP 5  MONITORING           OK
MT5 SIGNAL BRIDGE            OK
```

### Live Windows observation — 2026-08-24

The owner ran the application from the GitHub working copy on drive `A:` by clicking `start_bot.bat`. The application automatically entered the continuous loop and connected to the running MT5 terminal.

Observed configuration:

```text
DATA_SOURCE=mt5
MT5_SYMBOL=XAUUSD+
TRADING_SYMBOL=XAUUSD+
```

Observed result:

```text
MT5 provider connected: XAUUSD+
Ticks: 50
Level 2 book updates: 0
H1/M15/M5 bars: 60/60/100
has_data=True
Step 2: BUY, strength 17.66, confidence 28.24
Step 3: HOLD because google-generativeai was not installed
Step 4: SKIPPED
Step 5: no open trades
MT5 signal bridge: NEUTRAL signal written successfully
```

Interpretation:

- The MT5 connection, symbol, tick data, candles, news/macro enrichment and signal-file path are working.
- The broker/terminal did not provide Level 2 book updates during this observation. This must be checked in MT5 Market Depth; the system currently continues with ticks/candles when the book is empty.
- No trade was opened during this run because the Gemini package was missing and the decision became `HOLD`.
- The owner must keep `TRADING_ENABLED=0` while installing/testing Gemini and before the execution path is clarified.
- The log showed the same closed trade outcomes being written repeatedly in one loop iteration. `check_closed_deals()` returns all of today's closed deals, while `main.py` appends them again every cycle. This is a reporting bug that should be fixed by deduplicating logged deal IDs before trusting trade statistics.

### Windows safety-test finding — 2026-08-24

When the owner ran `test_session_risk.py` with the real MetaTrader5 package and terminal available, the suite returned `24/25`. The no-data execution test called `MT5Executor.execute()` directly with a high-confidence BUY and an empty snapshot. Because `TRADING_ENABLED=0` is currently enforced in `main.py`'s safety-gate path rather than inside `MT5Executor.execute()`, the direct test attempted `mt5.order_send()` and MT5 rejected it with retcode `10018` (market closed).

No order was reported as executed, but this exposed a serious safety gap: a direct executor call can bypass the master switch, and an empty snapshot could reach the order path when the market is open. Before further live/demo execution tests, add a master-switch check and empty/invalid-snapshot validation inside `MT5Executor.execute()`, make the no-data test use a mock or guaranteed non-trading executor, and add tests proving no order is sent when trading is disabled.

### End-to-end test hygiene finding — 2026-08-24

The first Windows run of `e2e_test.py` returned `31/31`, but its log displayed a masked key that matched a real key from the user's `.env`. The mocked Gemini module prevented a real API call, but the test failed to override the derived `config.GEMINI_API_KEYS` list, so it could still read a real secret. The test should set `config.GEMINI_API_KEYS = ["test-key"]` and the fake MT5 module should provide `history_deals_get = lambda ...: []`. An incremental patch named `e2e-test-secret-safe.patch` was prepared. Do not treat the e2e test as clean until this patch is applied and rerun.

### Task 1 — execution mode routing prepared — 2026-08-25

The owner selected EA-only execution. The local `.env` currently contains:

```env
EXECUTION_MODE=ea
TRADING_ENABLED=0
```

The execution-mode update was implemented and tested in the development workspace but still needs to be applied/committed to the owner's GitHub working copy. The update adds `EXECUTION_MODE=none|python|ea` handling:

- `none`: analysis only and neutralise the EA signal;
- `python`: Python MT5 execution only and neutralise the EA signal;
- `ea`: defer Step 4 to the EA and allow the bridge to carry an actionable signal only when all safety gates pass.

The patched workspace tests passed: `test_session_risk.py` 25/25, `test_markets.py` 28/28, `test_key_rotation.py` 7/7, `test_news.py` 11/11, `e2e_test.py` 32/32, Python compilation, and a safe EA-mode main pass with trading disabled. No real order was used for the EA-mode test.

### Task 3 — immediate Gemini key failover prepared — 2026-08-25

The owner requested no waiting when one Gemini key fails. Each key/model combination now receives one attempt only. A rate-limited or otherwise failed key is marked and the next key is tried immediately; there is no 3-second/6-second retry sleep between keys. The key cooldown remains only for later pipeline cycles and is configurable with `AI_KEY_COOLDOWN_MINUTES` (default 20); it is not a wait during current failover.

The key-rotation test was expanded to confirm per-minute rate-limit failover completes immediately and that later-cycle cooldown still works. The owner applied the update locally and confirmed `test_key_rotation.py` 9/9 passed. The update is ready to commit with the other Task 3 changes.

### Cleanup Task 2 — completed preparation — 2026-08-25

The owner approved repository cleanup. A local backup was created outside the repository at `../Gold-MT5-local-backup-20260825` (631 KB) containing runtime `data/`, `logs/` and the private `.env` when present.

Completed in the owner's Git working copy:

- `venv/` removed from Git tracking but retained locally;
- `__pycache__/` removed from Git tracking;
- generated `data/` files removed from Git tracking except `data/.gitkeep`;
- generated log files removed from Git tracking except `logs/.gitkeep`;
- `.gitignore` expanded for secrets, environments, caches, logs and generated data;
- temporary patch files removed from the repository.

Repository cleanup preparation was completed for the previous version: generated files were removed from Git tracking and retained locally. Future commits must still stage only intended source/documentation files and must not use `git add .` when runtime files are present.

### Version 0.6.4 — Pepperstone-ready Python execution foundation — 2026-08-26

A single downloadable source package is being prepared for the owner's new Pepperstone MT5 demo account. The package does not contain the private `.env`, virtual environment, runtime data or logs. It keeps the futures/Rithmic/Databento providers and adds a read-only Pepperstone broker diagnostic.

Implemented in the development workspace:

- Python position management: same-direction idempotence, opposite bot-position close/reverse, manual-position protection;
- broker-aware volume normalization and stop-distance validation;
- broker-supported filling-mode selection;
- optional explicit `MT5_TERMINAL_PATH` for multiple MT5 installations;
- clearer MT5 symbol-selection errors;
- `BROKER_NAME` and signal-age configuration;
- signal expiry field and MQL5 EA stale-signal rejection;
- supported `google-genai` SDK preferred, with temporary legacy fallback;
- configurable modern Gemini request timeout and unused AFC disabled;
- immediate Gemini key failover preserved;
- end-to-end test risk settings isolated from the user's personal `.env`, so the warning-mode sizing assertion remains valid when live demo settings cap `MAX_LOT_SIZE=0.01`;
- added `deduplicate_trade_outcomes.py` and report-level de-duplication so old repeated rows do not inflate statistics;
- added snapshot `data_quality` labels for live Level 2, live trade prints, estimated candle flow and unavailable Level 3;
- added required-margin preflight and MT5 `order_check()` before `order_send()`;
- added post-send position and history verification to `demo_order_test.py`; it now refuses to report success unless the position appears, closes and open/close deals are visible;
- one-command safe local test runner;
- explicit supervised `demo_order_test.py` for broker order plumbing (never a strategy test);
- report de-duplication utility and test;
- Pepperstone setup guide;
- README, version note and handoff updates.

The owner's selected first execution path is Python-only. EA support remains available but should be inactive while Python execution is tested. Pepperstone uses the exact symbol `XAUUSD`; the package includes the explicit terminal path and a read-only broker diagnostic. No broker credentials are included in the package.

Workspace validation for this foundation: the full local runner now passes all 12 test files. MQL5 compilation remains a Windows-side check.

### Version 0.6.5 — position-specific MT5 history reporting fix — 2026-08-26

The Pepperstone terminal returned the two real deals when queried by position ID:

```text
position 86160935 -> open deal 57028893, close deal 57028912
```

The date-range query returned only one non-XAUUSD balance/deposit record. This proved that the date-range path was unreliable for this terminal even though position-specific history worked.

Changed files:

- `step5_monitoring.py`: added position-specific closed-deal retrieval, original entry-side detection and deal-ID de-duplication;
- `step4_mt5_execution.py`: preserves the verified MT5 position ID in `ExecutionResult` metadata;
- `main.py`: persists strategy position IDs, records plumbing-test deal metadata separately, and passes IDs to Step 5 history logging; stale outcome state is ignored when the outcome CSV is empty so verified rows can be rebuilt;
- `risk_manager.py`: uses tracked strategy position history, includes commissions/fees, excludes explicit plumbing tests and removes the invalid future-date fallback;
- `robot_report.py`: separates plumbing-test outcomes from strategy statistics and displays original entry-side metadata when available;
- `GoldTradingEA.mq5`: protects manual/other-EA positions on hedging accounts, closes all bot positions before reversal, checks order results, selects broker filling mode and interprets fallback stops as points;
- `test_mt5_history.py`: fake-MT5 regression test for Pepperstone-style position history;
- `test_risk_history.py`: fake-MT5 regression test for daily risk PnL;
- `run_all_tests.py`: includes the history and risk tests;
- `AI_HANDOFF.md`: records the diagnosis, scope, test results and limitations.

The change does not alter the active settings. Windows verification must continue with:

```env
EXECUTION_MODE=python
TRADING_ENABLED=0
```

Tests for this change:

```text
Python compilation                  PASS
test_mt5_history.py                  6/6
test_risk_history.py                 2/2
test_reports.py                      2/2
test_python_execution.py            18/18
test_markets.py                     29/29
e2e_test.py                         32/32
ALL 12 LOCAL TEST FILES PASSED
```

Live Windows evidence: `history_deals_get(position=86160935)` returned both real Pepperstone deals with `last_error=(1, 'Success')`. The owner installed the 0.6.7 source and ran a safe pass with `TRADING_ENABLED=0`. The application imported close deal `57028912` once, then the report classified it as one broker-plumbing audit outcome and zero strategy trades. The owner chose to keep explicit demo plumbing tests separate from strategy performance, so the earlier verified position `86157466` must not be added to strategy statistics.

Current known limitations:

- the existing audit row remains in `trade_outcomes.csv` for evidence and is excluded from strategy metrics by `plumbing_test_deals.json`;
- old position IDs are recovered from prior executed rows, but a fresh bot should persist every newly verified strategy position;
- risk history now uses tracked strategy positions, but behavior must still be observed safely before trading is enabled;
- report PnL includes commission and fees, so it may differ from the MT5 History screen's displayed gross figure;
- the real strategy has not been shown profitable;
- MQL5 compilation and EA behavior remain unverified;
- the owner confirmed the active Windows `.env` intentionally uses `AI_MIN_SIGNAL_STRENGTH=7`; this is a deliberate setting, not a configuration error.

### Version 0.6.6 — reporting separation, risk-history fix and EA hardening — 2026-08-26

Implemented after the owner approved the complete fix plan:

- `main.py` records explicit plumbing-test deal IDs in `data/plumbing_test_deals.json` without deleting the audit CSV;
- `robot_report.py` excludes those IDs from strategy performance and displays them in a separate broker-plumbing section;
- closed-outcome side reporting now uses the original entry direction when the position history contains it;
- `risk_manager.py` uses tracked strategy position queries, includes profit, swap, commission and fee, excludes plumbing tests, and removes the invalid future-date fallback;
- `GoldTradingEA.mq5` now protects manual/other-EA positions on hedging accounts, handles all bot positions before reversal, checks trade results, selects symbol filling mode and applies fallback SL/TP values in points;
- `test_markets.py` is environment-independent;
- `e2e_test.py` forces its fake MT5 source and remains independent of the user's `.env`;
- added `test_risk_history.py` and expanded report/history tests.

Validation:

```text
ALL 12 LOCAL TEST FILES PASSED
```

The live Pepperstone terminal was not modified by these changes. The final Windows checks still require a safe `main.py` pass with `TRADING_ENABLED=0`, report review and MetaEditor compilation. No secrets were requested, stored or added.

### Version 0.6.7 — test data isolation — 2026-08-27

The end-to-end test now uses a temporary data and logs directory and restores all
runtime paths after completion. It no longer writes fake decisions, fake
positions, trade-guard state, risk state or signal files into the owner's real
runtime folders.

Validation:

```text
Full local runner: ALL 12 LOCAL TEST FILES PASSED
E2E test:          32/32
Runtime-data hash: unchanged before and after isolated E2E test
```

Windows safe validation after installation:

```text
Pepperstone connection: OK
XAUUSD data:            OK
Level 2:                live during the safe pass
Trading:                disabled
Strategy trades:        0
Plumbing tests:         1, excluded from strategy statistics
```

### Owner's current Windows operating context — updated 2026-08-27

The owner has migrated the demo test from Vantage to Pepperstone. The GitHub working copy is on drive `A:` and the application is run from:

```text
A:\gitHub\Gold-MT5\gold_trading_system_mt5
```

The Pepperstone MT5 executable is:

```text
C:\Program Files\Pepperstone MetaTrader 5\terminal64.exe
```

The active Pepperstone symbol is:

```text
XAUUSD
```

The Pepperstone demo account reports company `Pepperstone Limited` and server `PepperstoneUK-Demo`. The broker diagnostic found live bid/ask data, 10 Level 2 book levels for XAUUSD, minimum/step volume `0.01`, maximum volume `50.0`, stop/freeze levels `0`, and filling mode `2`.

The owner's selected first execution test is Python-only, with both execution modes preserved in the package. The safe local settings are:

```env
EXECUTION_MODE=python
TRADING_ENABLED=0
```

After diagnostics and supervised tests, Python mode may be selected. The EA remains available but must not run as a second active executor.

The owner wants to preserve Rithmic/Databento futures functionality. The current code supports one primary `DATA_SOURCE` per run; simultaneous MT5/futures data fusion remains a future feature. No additional platform integration is included in this release.

The owner also uses `start_report.bat`. It calls `robot_report.py`, reads the decision/trade CSV files and logs, and generates `data/robot_report.html`. It is a reporting tool; it does not place trades. New outcome logging is deduplicated, but old local report rows must be reviewed before trusting historical statistics.

### Historical test inconsistencies — resolved

Earlier versions had a broker-symbol assertion mismatch (`XAUUSD` versus broker suffixes) and an environment-dependent end-to-end assertion. The tests are now independent of the user's private `.env`; `test_markets.py` passes 29/29 and `e2e_test.py` passes 32/32.

### Backtest result observed

The current synthetic/demo backtest executed successfully but produced:

```text
Trades:             5
Win rate:           0%
Total return:      -15.86%
Profit factor:       0.0
Sharpe ratio:       -1.812
Maximum drawdown:   14.78%
```

This is not a real-market evaluation, but it confirms that profitability has not been established.

### Not yet verified

- one more Windows safe pass after the latest classification changes;
- the report showing zero strategy trades and one separate plumbing test;
- MQL5 EA and indicator compilation in MetaEditor;
- EA execution, reversal and trailing behavior on Pepperstone;
- the corrected risk-manager behavior in a live terminal with trading disabled;
- simultaneous-feed/data-fusion behavior;
- other-platform connectivity outside the current MT5/futures providers;
- slippage and live profitability.

Already verified on Pepperstone demo: Python opened and closed a 0.01-lot XAUUSD position, the live position appeared and disappeared, and MT5 history showed both the opening and closing deals. The Python position-history and risk-history regression tests now pass in the local workspace.

---

## 8. Safe Windows setup and test procedure

### Step 1 — Use one working copy

Use the folder that contains `main.py`, `config.py` and `.env.example`. Do not maintain separate edited copies on different drives.

Example:

```powershell
cd "C:\Users\<username>\Documents\Gold-MT5\gold_trading_system_mt5"
```

Confirm the files exist:

```powershell
dir main.py
dir .env.example
```

### Step 2 — Protect the secret file

Create `.env` from `.env.example` if it does not exist:

```powershell
Copy-Item .env.example .env
```

Keep `.env` local. Never commit it.

For the first tests, set:

```env
TRADING_ENABLED=0
```

Confirm that the exact MT5 Market Watch symbol is:

```text
XAUUSD
```

### Step 3 — Create a virtual environment

Use Python 3.11 or 3.12 if available because these versions are generally the safest choice for Windows MT5 integrations:

```powershell
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If Gemini testing is required:

```powershell
pip install google-generativeai
```

Do not paste the Gemini key into chat or into any Git-tracked file.

### Step 4 — Run local tests without live trading

```powershell
python -m compileall -q .
python demo_step2.py
python test_data_providers.py
python test_markets.py
python test_indicators_golden.py
python test_session_risk.py
python test_key_rotation.py
python test_news.py
python test_python_execution.py
python test_reports.py
python test_mt5_history.py
python e2e_test.py
```

The two known configuration-related failures described above may still appear until they are fixed.

### Step 5 — Test the MT5 connection

1. Open MetaTrader 5.
2. Log in to a demo account.
3. Open Market Watch.
4. Add `XAUUSD` if it is not visible.
5. Confirm that prices are updating.
6. Confirm the MT5 terminal is the same installation used in the signal-file path.

Then run:

```powershell
python mt5_test.py
```

This test should only read data. It should not place an order.

### Step 6 — Run the application in safe observation mode

Keep this in `.env`:

```env
DATA_SOURCE=mt5
TRADING_ENABLED=0
```

Run:

```powershell
python main.py
```

Expected safety behavior:

```text
STEP 1  DATA ACQUISITION     OK
STEP 2  MARKET ANALYSIS      OK
STEP 3  AI DECISION          HOLD or AI result
STEP 4  EXECUTION            SKIPPED
STEP 5  MONITORING           OK
```

Check that there is fresh data and that `has_data=True` appears in the output.

### Step 7 — Test the signal file

Check the configured MT5 file folder for:

```text
gold_signal.txt
```

Do not enable the EA AutoTrading switch yet. First compile both MQL5 files in MetaEditor and resolve all errors and warnings.

### Step 8 — Add Gemini only after data works

After MT5 data is confirmed, add the Gemini key locally to `.env`. Keep:

```env
TRADING_ENABLED=0
```

Run `python main.py` and confirm that Step 3 produces an AI decision while Step 4 remains skipped.

### Step 9 — Demo trading only after execution mode is fixed

Do not enable real or demo auto-trading until the application has an explicit `EXECUTION_MODE` and it is clear whether Python or the EA is responsible for orders.

When demo trading is eventually enabled:

- use the smallest broker-supported lot size;
- use a demo account;
- watch the first trades manually;
- confirm SL/TP placement;
- confirm the daily loss breaker;
- confirm news blackout behavior;
- confirm only one order is created per signal;
- keep logs and decision records.

---

## 9. Recommended next development tasks

Priority order after version 0.6.7:

1. Compile `GoldTradingEA.mq5` and `GoldSignalIndicator.mq5` in MetaEditor.
2. Test EA-only mode separately; never run Python and EA as simultaneous order
   executors.
3. Observe the corrected risk-manager history path safely on demo; do not enable
   trading until the risk output is understood.
4. Supervise one natural Python strategy signal on demo using 0.01 lots only,
   then return `TRADING_ENABLED=0` after verification.
5. Verify SL/TP, close, reverse, cooldown, daily cap and report outcome behavior.
6. Record real Pepperstone data and backtest with spread, commission, slippage,
   drawdown, profit factor and out-of-sample periods.
7. Preserve and improve the Rithmic/Databento futures and Level 3/MBO paths.
8. Keep cTrader and other unrequested platforms out of the project.

---

## 10. Version update checklist

After every meaningful improvement:

1. Update the version number in the source or release note.
2. Update the `Last updated` date at the top of this file.
3. Add a new entry to the version history below.
4. Record changed files and configuration changes.
5. Record any migration steps for the user's `.env`.
6. Run the relevant tests.
7. Record exact test results, including failures.
8. Update the safe run instructions if commands changed.
9. Confirm no secrets were added.
10. Commit and push this file together with the code changes.

Recommended Git workflow:

```powershell
git pull
git status
git checkout -b improvement/short-description
# make and test changes
git add .
git commit -m "Describe the improvement"
git push -u origin improvement/short-description
```

After review, merge the branch into `main`. Do not commit `.env`, `venv`, passwords, API keys or generated private data.

---

## 11. Version history

### 2026-08-27 — Version 0.6.7 — test data isolation

- Isolated the end-to-end test's generated files in a temporary data/logs directory.
- Confirmed the real runtime files remain unchanged after the test.
- Full local validation remains 12/12 test files passed.
- Windows safe validation completed: Pepperstone/XAUUSD data worked, Level 2 was live during the pass, one plumbing test was classified separately, and trading remained disabled.
- No secrets were requested, stored or added. Trading remains disabled.

### 2026-08-26 — Version 0.6.6 — reporting separation, risk-history fix and EA hardening

- Added separate plumbing-test deal metadata and excluded those audit rows from strategy statistics without deleting the CSV.
- Corrected outcome side display to use the original entry direction.
- Updated the risk manager to use tracked strategy position queries and include commission/fees.
- Hardened the MQL5 EA for hedging accounts and manual/other-EA position protection; MetaEditor compilation remains a user-side check.
- Fixed environment-dependent market and end-to-end tests.
- Added risk-history coverage and expanded local tests.
- Full local validation: all 12 test files passed.
- No secrets were requested, stored or added. Trading remains disabled for Windows verification.

### 2026-08-26 — Version 0.6.5 — position-specific MT5 history reporting fix

- Confirmed from the owner's Pepperstone terminal that `history_deals_get(position=86160935)` returns open deal `57028893` and close deal `57028912`.
- Confirmed that the date-range query returns only a balance/deposit record for this terminal, so it cannot be the primary closed-trade lookup.
- Added tracked bot position IDs and position-specific Step 5 history retrieval.
- Added `position_id` metadata to successful Python execution results.
- Added recovery from `demo_order_test_result.json` and prior executed decision rows.
- Preserved deal-ID/signature de-duplication and rebuilt-outcome behavior when the CSV is empty.
- Added `test_mt5_history.py` with 6/6 checks and included it in the local runner.
- Added `test_risk_history.py` with 2/2 checks.
- Separated explicit plumbing-test outcomes from strategy statistics without deleting the audit CSV.
- Corrected future outcome side reporting to use the original entry direction.
- Fixed environment-dependent `test_markets.py` and `e2e_test.py`; the full runner now passes all 12 local test files.
- Updated `risk_manager.py` to use tracked strategy position history and include commission/fees.
- Hardened the MQL5 EA for hedging accounts, manual-position protection, reversal failures, broker filling and fallback point units. MetaEditor compilation remains required.
- Windows 0.6.5 validation completed with trading disabled: close deal `57028912` was imported once.
- The owner chose to keep explicit plumbing-test outcomes separate from strategy performance; do not import position `86157466` into strategy metrics.
- No secrets were requested, stored or added. Trading remains disabled.

### 2026-08-24 — Initial AI handoff

- Reviewed the public GitHub repository.
- Downloaded and tested the core Python application.
- Confirmed the intended runtime profile is MT5-only with broker symbol `XAUUSD+`.
- Confirmed safe demo pipeline runs successfully.
- Confirmed most automated tests pass.
- Documented two current test/configuration inconsistencies.
- Documented that live MT5, Gemini and MQL5 behavior still require Windows validation.
- Documented duplicate-execution risk between Python MT5 execution and the EA signal path.
- Documented the need to remove the committed virtual environment and generated files.
- Added the owner's first live Windows/MT5 observation: ticks and candles work, Level 2 is empty, Gemini is not installed, no trade was opened, and repeated outcome logging was observed.
- Added the owner's confirmed operating context: Vantage demo account, GitHub working copy on drive A:, `start_bot.bat` launcher, `start_report.bat` reporting, future futures-feed preservation, and the current absence of simultaneous feed fusion or a selected execution path.
- Confirmed a safe real Gemini call: key #1 was rate-limited, key #2 answered `HOLD @ 75%`, no trade occurred because `TRADING_ENABLED=0`, and the signal bridge wrote `NEUTRAL`.
- Confirmed the current Gemini SDK is deprecated and should be migrated to `google-genai` before further production work.
- Implemented and locally verified immediate Gemini key failover with no artificial wait; `test_key_rotation.py` passed 9/9 and the cooldown setting was documented in `.env.example`.
- Prepared Pepperstone-ready package work: Python position management, broker diagnostics, explicit terminal path, modern Gemini support, signal expiry and portable documentation.
- Fixed MT5 market-book type mapping after Pepperstone diagnostic: MT5 type 1 is sell/ask and type 2 is buy/bid; the prior provider incorrectly treated type 0/other as the bid/ask split.
- Confirmed Pepperstone MT5 XAUUSD provides 10 Level 2 book levels during diagnostic testing.
- Corrected MT5 BookInfo mapping in the provider and read-only test: `type=2` is a buy/bid entry and `type=1` is a sell/ask entry. Added retries after book subscription so a populated Level 2 book is not falsely reported as empty. Local test suite remained fully green.
- The first explicit demo-order script reported an apparent success but Pepperstone history showed no order; this was treated as unverified and fixed with post-send position/history verification in `demo_order_test.py`.
- Pepperstone later showed the open and close deals in a wide history query: open deal `57028893`, close deal `57028912`, position `86160935`, close PnL `-0.11`. The verification utility was updated to query history by position ID and use a wide fallback, avoiding broker date-range behavior.
- Monitoring history fallback was updated to use a wide broker-history query when a narrow date query returns no closed deals; persistent deal IDs/signatures prevent duplicates.
- Added margin preflight and `order_check()` so an insufficient-margin order is rejected before `order_send()`.

---

## 12. Prompt for the next AI or developer

Copy the following information when starting a new development conversation:

```text
This is the Gold Trading System project, currently packaged as the Pepperstone-ready MT5-data foundation.

Repository:
https://github.com/jafarimahdi/Gold-MT5

Please read gold_trading_system_mt5/AI_HANDOFF.md first.
The current broker test is Pepperstone Limited, server PepperstoneUK-Demo, using the exact symbol XAUUSD and terminal64.exe at:
C:\Program Files\Pepperstone MetaTrader 5\terminal64.exe

The package supports `EXECUTION_MODE=none|python|ea`; the owner's first supervised execution path is Python. The safe starting settings are `EXECUTION_MODE=python` and `TRADING_ENABLED=0`. Never request or expose API keys, passwords or private credentials.

Current validated facts:
1. Pepperstone MT5 connection works for the exact symbol `XAUUSD`.
2. Pepperstone XAUUSD previously provided 10 Level 2 book levels; at the later daily break the diagnostic showed zero levels, so the feed must be treated as time-dependent.
3. Position-specific `history_deals_get(position=86160935)` returned open deal `57028893` and close deal `57028912` with `last_error=(1, 'Success')`.
4. Pepperstone date-range history returned only a balance/deposit record during this investigation; version 0.6.7 tracks strategy position IDs and queries by position for reporting and risk checks.
5. The full 0.6.7 local runner passes all 12 test files, including position-history reporting, risk-history, plumbing classification and test-isolation checks.
6. MT5 CFD data has no Level 3 events; quote tick last/volume may be zero, so some CVD/footprint values are estimated.
7. MQL5 compilation and EA behavior are not yet verified.
8. The current modern Gemini client has a configurable request timeout; keep the latest timeout behavior documented by the current source.

First ask me for the latest git commit, the current sanitized `.env` configuration, and the latest safe test output if they are not already available. Preserve and update this handoff after every version improvement. Do not delete or move files without explaining why and asking first.
```

---

## 13. Security rules

- Never commit `.env`.
- Never put an API key in this file.
- If a key was ever pushed to the public repository, revoke it and create a new one.
- Do not paste MT5 passwords or Gemini keys into chat.
- Test with `TRADING_ENABLED=0` first.
- Do not run Python execution and the EA execution path simultaneously until an explicit mode switch is implemented.
- Treat all automated trading as high risk. A passing software test does not prove profitability or guarantee safe trading.
