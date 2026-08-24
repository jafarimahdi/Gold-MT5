# CHANGES — Analysis Precision & News-Time Behaviour Upgrade

This document lists every change made to improve the accuracy of the gold
market analysis and the behaviour of the robot around news events.

All changes verified: **36/36** Step-2 unit checks and **31/31** end-to-end
integration checks pass.

---

## 1. LEVEL 2 (bid/ask depth) analysis — new `OrderBookDepthAnalyzer`

| Change | How it improves results |
|---|---|
| **Microprice** (size-weighted mid, Stoikov formula) | A better estimate of fair value than the plain mid-price. When bid depth is thicker than ask depth, fair value tilts toward the ask — capturing real bullish/bearish pressure that the mid-price hides. |
| **Depth imbalance** over top-N levels | Measures whether resting liquidity is biased to the buy or sell side — a leading indicator of short-term direction. |
| **Order Flow Imbalance (OFI)** from successive book snapshots | OFI (Δbid size − Δask size) is the industry-standard leading predictor of short-term price moves — far more predictive than end-of-bar delta. |
| **Liquidity slope + concentration** | Detects thin books (liquidity concentrated at the top level) → warns of slippage risk before entries. |
| **Absorption detection** | Flags large walls being eaten at the same price without the market trading through — a classic sign of aggressive hidden buying/selling. |

## 2. LEVEL 3 (order events) analysis — upgraded `Level3OrderBookAnalyzer`

| Change | How it improves results |
|---|---|
| **Event-level OFI** (NEW/CANCEL/MODIFY/FILL accounting) | Same OFI concept but computed from individual order events (Databento MBO) — the highest-resolution order-flow signal available. |
| **Aggressive flow ratio** (buy size / total aggressive size) | Quantifies who is *aggressively* initiating — a better measure of conviction than total volume. |
| **Aggressor streaks** | Detects persistent same-side aggression (3+ consecutive market buys/sells) = momentum/urgency. |
| **Iceberg detection** | Repeated same-size orders at the same price = hidden institutional size being worked. |
| **Large order events** | Counts orders above a size threshold — institutional presence. |
| **MODIFY event support** | Order book reconstruction now stays correct when orders are amended, not just added/cancelled. |

## 3. Trade-side classification — tick rule

| Change | How it improves results |
|---|---|
| **Tick-rule side inference** | When a feed does not label the aggressor side, the side is inferred from price direction (up = buyer-initiated, down = seller-initiated). Fixes a silent data-quality bug that was corrupting CVD/Delta/Footprint. |

## 4. Correlations on log-returns

| Change | How it improves results |
|---|---|
| **`MacroAnalyzer.pearson(use_returns=True)`** | Correlations are now computed on log-returns, not raw price levels. Raw level correlations are statistically meaningless for trending series (they drift toward ±1); return correlations are the only valid measure of co-movement. |

## 5. VWAP z-score bands

| Change | How it improves results |
|---|---|
| **VWAP standard deviation + z-score** | Adds objective "how far from fair value" bands. Combined with the regime filter, this enables mean-reversion entries at extremes and avoids them mid-trend. |

## 6. Regime detection

| Change | How it improves results |
|---|---|
| **`regime` = TREND / RANGE / NEUTRAL (from ADX)** | The signal engine now adapts: in RANGE it fades VWAP extremes (mean reversion); in TREND it does not fight the trend. Trend-following signals in ranges — and reversion signals in trends — are the two classic ways bots bleed money. |

## 7. CVD–price divergence

| Change | How it improves results |
|---|---|
| **Divergence detector** | Price making a higher high while CVD is negative (or lower low while CVD positive) = absorption/reversal warning. This is a high-value, well-known order-flow signal now fed into the composite score with a strong weight. |

## 8. NEWS-TIME state machine (the key news improvement)

`EconomicCalendar.news_state()` classifies "now" against upcoming high-impact
events into three states (windows configurable in `.env`):

| State | Window (default) | What the robot does |
|---|---|---|
| **QUIET** | > 30 min before event | Trades normally |
| **WARNING** | 30–15 min before | Signal confidence cut to 70%; Step 4 **widens the stop 1.5×** and **cuts position size to 50%** |
| **BLACKOUT** | 15 min before → 30 min after | **No new entries** — signal forced NEUTRAL (confidence 0) *and* Step 4 refuses to execute even if the AI votes BUY/SELL |

This is defence-in-depth: the signal engine and the execution layer both
independently block trading during the highest-volatility window. Trading
into FOMC/CPI/NFP is the single biggest source of slippage losses — this
eliminates that.

## 9. Risk-based position sizing (Step 4)

| Change | How it improves results |
|---|---|
| **`compute_lot_size()`** | Lots are now derived from `equity × risk% ÷ (stop distance × contract size)` instead of a fixed lot. Every trade risks the same % of equity regardless of volatility — the foundation of survivable money management. Falls back to the fixed size when equity is unknown. |

## 10. Decision journal

| Change | How it improves results |
|---|---|
| **`data/decisions_log.csv`** | Every pipeline pass is appended (signal, AI decision, execution status, news state, regime, divergence, reason). This is the dataset you will use to tune thresholds and validate the strategy — you cannot improve what you do not measure. |

---

## Files changed

- `step2_market_analysis.py` — dataclasses, `OrderBookDepthAnalyzer` (new),
  `Level3OrderBookAnalyzer`, `OrderFlowAnalyzer`, `VolumeProfileAnalyzer`,
  `MacroAnalyzer`, `EconomicCalendar`, `SignalEngine`, `analyze_market`,
  `format_snapshot`, synthetic data generator.
- `config.py` — news windows, contract size, equity, sizing/news params.
- `step4_mt5_execution.py` — news gates, widened stops, reduced size,
  risk-based sizing.
- `main.py` — decision journal CSV.
- `demo_step2.py` — 36 unit checks incl. L2/L3/news-time.
- `e2e_test.py` — 31 integration checks incl. news-time through Step 4.
- `.env.example`, `README.md` — documentation.

---

# CHANGES (round 2) — Data providers, credential handling & MT5 bridge

## 11. Data-provider layer (`data_providers.py`)

| Change | How it improves results |
|---|---|
| `DemoProvider` / `RithmicProvider` / `DatabentoProvider` behind one `get_provider()` factory | Switching vendors = one line in `.env` (`DATA_SOURCE=`). The whole pipeline is vendor-agnostic. |
| Rithmic L2/L3 mapping (`handle_depth`, `handle_order_event`, `handle_trade`) | Every Rithmic callback maps to the exact Step-2 schema (book_updates → OFI, order_events → L3 analyzer, trades → CVD/footprint/candles). |
| Databento MBO/MBP-10/trades row mappers | Databento's `action`/`side` codes map correctly to Step-2 events (incl. `T` → aggressor market fill matching the L3 convention). |
| `trades_to_candles()` | Builds OHLCV candles from any trade stream so technicals/macro work on live data. |
| Verified by `test_data_providers.py` (27 checks) | Proves Rithmic- and Databento-shaped data flows through **every** Step-2 function with no errors. |

## 12. Easy credential rotation

| Change | How it helps |
|---|---|
| Credentials read from `.env` at connect-time + `config.reload_env()` | Rotating Rithmic demo usernames/passwords (they expire) is a `.env` edit + restart — no code changes. |
| `RITHMIC_SYSTEM=Rithmic Paper Trading` default | Correct demo-system name out of the box; swap to your live system name when subscribing. |
| `DATABENTO_*` settings | Adding Databento later = paste key + set `DATA_SOURCE=databento`. |

## 13. MT5 indicator + auto-trading bridge

| Change | How it helps |
|---|---|
| `mt5_signal_bridge.py` writes a simple `key=value` signal file | No JSON parser needed in MQL5; the EA/indicator read it with plain string functions. |
| `GoldTradingEA.mq5` (Expert Advisor) | Trades BUY/SELL automatically: confidence ≥ 70% gate, news-blackout block, ATR SL/TP, closes the opposite position before reversing. |
| `GoldSignalIndicator.mq5` (indicator) | Draws BUY/SELL arrows + a corner label (direction/confidence/news state) on the chart. |
| Same rules on both sides | Python Step 4 and the MQL5 EA enforce identical gates (confidence + news time), so behaviour is consistent whichever execution path you use. |

## 14. Small robustness fix

- `VolumeProfileAnalyzer.analyze()` now returns a default metrics object for
  empty input instead of crashing on `close[-1]`.

---

# CHANGES (round 3) — Two-market support: futures DATA vs CFD TRADE

## 15. Market & symbol registry (`markets.py`)

| Change | How it improves results |
|---|---|
| `MarketProfile` registry (GC 100oz futures, MGC 10oz micro futures, XAUUSD CFD) with aliases, contract size, tick size/value | The app now *recognises* every common gold name on both sides of the pipeline. |
| `normalize_symbol()` | "GCZ4", "GC.n.0", "GC=F", "MGCZ24", "XAUUSD.i/.m", "GOLD", "GOLDUSD", "XAU/USD" all map to a canonical market id — so vendor/broker name differences never break anything. |
| `resolve_market(name, role)` + advisory notes | Warns if you point the *data* side at a CFD or the *trade* side at futures. |

## 16. Price-agnostic analysis (movement, not price)

| Change | How it improves results |
|---|---|
| Analysis strictly on the DATA feed; `data_symbol` / `trade_symbol` / `data_market` / `trade_market` now travel on every snapshot | The two price levels can never be accidentally mixed. |
| `atr_pct()` / `scale_distance()` helpers | Volatility is expressed as % of price and re-anchored to whichever price is in play. |
| Step 4 re-anchors futures ATR to the live CFD price: `atr = src_atr × (cfd_price / futures_price)` | SL/TP reflect market movement, correct even though futures and CFD quotes differ. |
| Signal bridge emits `sl_pct` / `tp_pct` (percentage offsets) | The MQL5 EA computes SL/TP from its own live CFD price — fully decoupled from the futures price in the file. |
| `GoldTradingEA.mq5` uses `sl_pct`/`tp_pct` against `SymbolInfoDouble()` | The EA's stops are always anchored to the exact CFD market it is trading. |

## 17. Manual market selection (`setup_markets.py`)

| Change | How it helps |
|---|---|
| Interactive wizard picks DATA and TRADE markets separately and writes `.env` | Easy, error-proof switching between GC/MGC ↔ XAUUSD/GOLD. |
| `--check` verification mode | Shows the resolved mapping + symbol-recognition table without prompts. |
| `--data X --trade Y` one-liner | Scriptable setup. |
| Manual confirmation step ("are you receiving the right Rithmic data? is the CFD symbol in MT5 Market Watch?") | Matches your workflow of validating the demo feed first. |

## 18. Unified DATA-side symbol

- `DATA_SYMBOL` (default GC) is the feed market; `MT5_SYMBOL` (default XAUUSD)
  is the trade market. `main.py` no longer passes the trade symbol into the
  data provider (would have made a live provider subscribe to the CFD name).
- Providers tag every payload with both market identities.

Verified: 36/36 Step-2 checks, 27/27 provider checks, 28/28 market checks,
31/31 end-to-end checks.

---

# CHANGES (round 4) — Weekend/no-data resilience + risk & validation tools

## 19. Weekend / no-data protection (the key ask)

| Change | How it prevents problems |
|---|---|
| `session.py` — trading-session calendar (`is_market_open`, `describe_now`, `next_open_time`) | The bot now KNOWS when gold is closed (weekends, daily breaks). It logs `SAFETY: SESSION CLOSED` and skips trading instead of acting on an empty feed. |
| Feed heartbeat in every provider (`last_data_ts`, `data_age_seconds`, `has_data`) | A silent Rithmic feed is detected: `SAFETY: FEED STALE/EMPTY` blocks trading once data is older than `STALE_DATA_SECONDS` (default 300s). |
| Empty-feed fixes in Step 2 | `analyze_market({})` now returns NEUTRAL with **zero** strength and **zero** confidence (was: 50% misleading "agreement"). Fixed an empty-tick crash and an RSI-default bug that made an empty feed read as oversold. |
| `ReplayProvider` + `record_market_data()` | Record a live session (`RECORD_DATA=1`) and replay it offline on weekends (`DATA_SOURCE=replay`) so testing never stalls. |
| `main.py` safety gates run before execution | Session → feed → risk, in order; any failure forces a HOLD decision, so Steps 3–4 can never fire into a closed/stale market. |

## 20. Risk circuit-breaker (`risk_manager.py`)

- Daily-loss limit (halt for the day if today's PnL ≤ -DAILY_LOSS_LIMIT_PCT %).
- Max-drawdown limit (halt if equity drops MAX_DRAWDOWN_PCT % from peak).
- Halt state is **persisted** to `data/risk_state.json`, so a restart cannot
  reset it; expires automatically at UTC midnight.

## 21. Backtest harness (`backtest.py`)

- Replays history through the REAL `analyze_market()` and measures win rate,
  total return, profit factor, Sharpe (annualised) and max drawdown.
- Honest finding on synthetic data: the current engine has **no edge**
  (negative expectancy) — exactly why backtesting-before-live matters.

## 22. Golden indicator tests (`test_indicators_golden.py`)

- EMA/RSI/ATR/MACD verified against independent reference implementations;
  analytic cases (RSI monotonic == 100/0, ATR constant range, Bollinger flat);
  ADX behaviour (high in trend, low in noise). Cross-checks TA-Lib if present.
  This locks indicator correctness against silent regressions.

## 23. PnL feedback loop + spread monitor

- `data/trade_outcomes.csv` records realised MT5 deals (`check_closed_deals`),
  closing the signal→decision→execution→outcome loop.
- `spread_monitor.py` warns when the futures↔CFD basis widens beyond
  `SPREAD_ALERT_PCT` (dislocation early-warning).

## 24. Config reloading fixed for real

- `config.reload_env()` now re-binds ALL constants (not just os.environ), and
  keys removed from `.env` revert to defaults. `main.py --loop` re-reads `.env`
  every cycle — so credentials/settings edits apply without a restart.

Verified: 36 Step-2 + 27 provider + 28 market + 19 indicator + 25 resilience
+ 31 end-to-end = 166 checks pass.
