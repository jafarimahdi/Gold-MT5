# Gold Trading System — AI Handoff and Backup Information

**Purpose:** This file is the durable project handoff for future development. Any new developer or AI assistant should read this file before changing the application.

**Last updated:** 2026-08-24  
**Repository:** https://github.com/jafarimahdi/Gold-MT5  
**Branch reviewed:** `main`  
**Commit reviewed:** `5e718a3` (`upload app`)  
**Application directory:** `gold_trading_system_mt5/`

> Keep this file inside the application folder and update it after every meaningful version improvement. Never put real API keys, passwords, tokens, private certificates, or the real `.env` file in this document.

---

## 1. Project summary

This project is a Python-based automated gold-trading system for MetaTrader 5. It is designed to work with the broker's gold symbol, currently:

```text
XAUUSD+
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

The owner's local `.env` was supplied without secrets. The intended configuration is:

```env
DATA_SOURCE=mt5
MT5_SYMBOL=XAUUSD+
TRADING_SYMBOL=XAUUSD+
DATA_SYMBOL=XAUUSD+
DATA_MARKET=XAUUSD
TRADE_MARKET=XAUUSD
MT5_LOGIN=0
```

### Meaning of the symbol settings

- `XAUUSD+` is the exact broker symbol used by MT5.
- Internally, `markets.py` normalizes `XAUUSD+` to canonical market ID `XAUUSD`.
- The plus sign must not be removed when communicating with MT5 if that is the symbol displayed by the broker.
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

### Cleanup Task 2 — completed preparation — 2026-08-25

The owner approved repository cleanup. A local backup was created outside the repository at `../Gold-MT5-local-backup-20260825` (631 KB) containing runtime `data/`, `logs/` and the private `.env` when present.

Completed in the owner's Git working copy:

- `venv/` removed from Git tracking but retained locally;
- `__pycache__/` removed from Git tracking;
- generated `data/` files removed from Git tracking except `data/.gitkeep`;
- generated log files removed from Git tracking except `logs/.gitkeep`;
- `.gitignore` expanded for secrets, environments, caches, logs and generated data;
- temporary patch files removed from the repository.

The next cleanup step is to review/stage only the intended source, documentation and `.gitignore` changes, then commit them. Do not use `git add .` until the staged file list has been checked because the local virtual environment and runtime files remain on disk.

### Owner's current Windows operating context — 2026-08-24

The owner confirmed that the GitHub working copy is on drive `A:` and is the same application version being run locally. The application is launched by clicking:

```text
A:\gitHub\Gold-MT5\gold_trading_system_mt5\start_bot.bat
```

The batch file changes into the application directory, starts/uses the local Python virtual environment, launches the continuous `main.py --loop`, and the MT5 terminal is available to the provider. The current broker is Vantage and the account is demo.

The owner wants to:

- continue using the current Vantage MT5 CFD for demo testing;
- keep the futures/Rithmic/Databento capabilities in the code for future testing;
- potentially support both MT5 and futures data in a future data-fusion design;
- consider Pepperstone or Interactive Brokers later, with the broker choice not yet final;
- keep automatic demo trading possible, but the execution path (Python versus EA) is not yet selected.

Important architecture clarification: the current code supports ONE configured `DATA_SOURCE` per run. It can use futures data for analysis and MT5 for execution, but it does not currently combine MT5 and futures feeds simultaneously. Combining both feeds requires a new data-fusion layer with timestamp alignment, source priority and conflict handling.

The owner also uses `start_report.bat`. It calls `robot_report.py`, reads the decision/trade CSV files and logs, and generates `data/robot_report.html`. It is a reporting tool; it does not place trades. The current report data must not be trusted until the repeated closed-deal logging bug is fixed.

### Known test inconsistencies

`test_markets.py` returned `27/28`.

The failed check expects `DATA_SYMBOL=XAUUSD`, while the current configuration defaults to `GC` for the futures/data design. For `DATA_SOURCE=mt5`, the provider actually uses `MT5_SYMBOL`. The test and configuration need to be made consistent.

`e2e_test.py` returned `30/31`.

The failed check expects `main.py` to report `mt5`, but no real `.env` exists in the repository and the code therefore falls back to `DATA_SOURCE=demo`. The test should explicitly set its configuration rather than depending on a private `.env` file.

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

- real MT5 connection;
- exact broker symbol behavior for `XAUUSD+`;
- real MT5 Level 2 data;
- broker lot-size and stop-distance rules;
- real order placement;
- Gemini API responses using the configured models;
- live news/calendar accuracy;
- MQL5 EA and indicator compilation;
- duplicate-execution behavior;
- slippage and live profitability.

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
XAUUSD+
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
python e2e_test.py
```

The two known configuration-related failures described above may still appear until they are fixed.

### Step 5 — Test the MT5 connection

1. Open MetaTrader 5.
2. Log in to a demo account.
3. Open Market Watch.
4. Add `XAUUSD+` if it is not visible.
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

Priority order:

1. Clean the GitHub repository by removing `venv/`, `__pycache__/`, generated logs and unwanted generated data.
2. Expand `.gitignore` beyond only `.env`.
3. Fix the duplicate/inconsistent `DATA_SYMBOL` settings in `.env.example`.
4. Fix `test_markets.py` and `e2e_test.py` so tests do not depend on a private `.env`.
5. Add `EXECUTION_MODE=none|python|ea`.
6. Make observation-only mode the default.
7. Unify Python and EA position-sizing rules.
8. Improve symbol validation and fail clearly if `XAUUSD+` is absent in MT5.
9. Add broker-specific checks for volume step, minimum volume, stops level and filling mode.
10. Add a test that proves the EA/Python duplicate-execution risk cannot occur.
11. Record real demo data and backtest it with out-of-sample periods.
12. Paper trade for multiple weeks before considering real money.

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

---

## 12. Prompt for the next AI or developer

Copy the following information when starting a new development conversation:

```text
This is the Gold Trading System project.

Repository:
https://github.com/jafarimahdi/Gold-MT5

Please read gold_trading_system_mt5/AI_HANDOFF.md first.
The intended runtime is Windows + MetaTrader 5 using the broker symbol XAUUSD+.
The project must remain in safe observation mode until the execution path is clarified.
Do not request or expose API keys, passwords or private credentials.

Current known issues:
1. The project contains generated files/venv that should be removed from Git.
2. test_markets.py has one DATA_SYMBOL configuration mismatch.
3. e2e_test.py has one DATA_SOURCE/environment-dependent mismatch.
4. Python direct execution and the MQL5 EA signal path can both be active; add an explicit execution mode before auto-trading.
5. Live MT5 and MQL5 behavior have not yet been verified.

First ask me for the latest git commit, the current sanitized .env configuration, and the latest safe test output if they are not already available.
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
