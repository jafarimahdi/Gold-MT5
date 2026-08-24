# CHANGES — Better-Result Improvements (MT5 version)

Date: 2026-08-19

Seven improvements. Each is listed with WHERE it is and WHY it helps.

---

## 1. Multi-timeframe confirmation — H1 → M15 → M5 must agree with M1

**Why:** a single 1-minute signal is noisy. When the 1-hour, 15-minute and
5-minute trends all point the same way, the signal is far more reliable.
Disagreement filters out trades that fight the bigger picture.

**Where:** `step2_market_analysis.py` (`_detect_tf_trend`, `_detect_mtf_trends`,
SignalEngine weighted votes), `data_providers.py` (fetches H1/M15/M5 candles),
`config.py` (`CONFIRM_TIMEFRAMES=H1,M15,M5`).

## 2. Anti-overtrading guard — cooldown + daily trade cap

**Why:** a scalper bot that opens a position on every small signal "churns" —
flipping BUY/SELL rapidly and paying the spread each flip, which bleeds the
account. `COOLDOWN_MINUTES` (default 15) and `MAX_TRADES_PER_DAY` (default 20,
raised from 10 at your request) stop it.

**Where:** `trade_guard.py` (NEW, persisted state), `main.py` (gate + record).

## 3. Spread guard

Blocks trades when the MT5 bid-ask spread is wider than `MAX_SPREAD_PCT`
(default 0.05%) — entering into a wide spread costs instant money.

## 4. Trailing stop-loss

`GoldTradingEA.mq5` — `InpUseTrailing` + `InpTrailingPoints` lock in profit.

## 5. Order Flow Imbalance (OFI) + Absorption NOW WORK — persistent book

**Why (important):** OFI (order flow imbalance) and absorption detection are
two of the most predictive Level-2 signals, but they need to compare the
CURRENT order book against the PREVIOUS one. Before this change, each cycle
built a fresh book and forgot it, so OFI was always 0 and absorption never
triggered. The book state is now remembered across cycles (in memory) and
persisted to `data/last_book_state.json` (survives a restart).

**Where:** `step2_market_analysis.py` (`_get_persistent_l2`, `_save_book_state`),
`data_providers.py` (MT5 provider samples the book twice per pass).
Also fixed: when ticks are empty, the L2 metrics (OFI etc.) are no longer
dropped.

**Verified:** bids +30 → OFI +30; asks +40 → OFI −10 (cumulative). Correct.

## 6. Order blocks / supply-demand zones (smart money) — NEW

**Why:** "smart money" zones (where big players bought/sold) act as support
and resistance. The robot now detects them from swing highs/lows:
- a swing high → **supply zone** (resistance above price)
- a swing low → **demand zone** (support below price)
The nearest support/resistance are computed, shown in the snapshot, and vote
in the signal: price near a demand zone = bullish bounce; near a supply zone =
bearish rejection.

**Where:** `step2_market_analysis.py` (`_detect_order_blocks`, `_nearest_zones`,
SignalEngine zone votes, snapshot fields, display line "Zones: support … |
resistance …"), `config.py` (`ORDER_BLOCKS_ENABLED`).

**Verified:** 8 zones detected on the demo data; support 2021.71 below price,
resistance 2039.36 above price.

## 7. Bug fix — inline comments in `.env` no longer break values

`.env` values with trailing `# comments` were misread; `config.py` now strips
inline comments, and `.env` files put comments on their own lines.

---

## 8. Automatic file maintenance (NEW — keeps the app light long-term)

**Why:** a few files would otherwise grow forever:
- `logs/trading_YYYYMMDD.log` (one new log per day)
- `data/decisions_log.csv` (one row per analysis cycle)
- `data/trade_outcomes.csv` (one row per closed trade)
- `data/record_*.json` (one file per recorded session)

**Where:** `maintenance.py` (NEW) — runs automatically once per day from the
pipeline. It:
- deletes log files older than `LOG_RETENTION_DAYS` (default 7),
- trims the decision/outcome CSVs to the latest N rows
  (`DECISIONS_LOG_MAX_ROWS`=5000, `OUTCOMES_LOG_MAX_ROWS`=2000),
- deletes recordings older than `RECORD_RETENTION_DAYS` (default 30).

You can also run it manually any time: `python maintenance.py` (prints sizes).

**Verified:** 60-day-old files deleted, 1-day-old files kept, a 6000-row CSV
trimmed to 5000 with the header preserved. All 166 tests still pass.

## How to tune (all in `.env`)

    CONFIRM_ENABLED=1
    CONFIRM_TIMEFRAMES=H1,M15,M5
    MAX_SPREAD_PCT=0.05
    ORDER_BLOCKS_ENABLED=1
    COOLDOWN_MINUTES=15
    MAX_TRADES_PER_DAY=20
    MAINTENANCE_ENABLED=1
    LOG_RETENTION_DAYS=7
    DECISIONS_LOG_MAX_ROWS=5000
    OUTCOMES_LOG_MAX_ROWS=2000
    RECORD_RETENTION_DAYS=30

## Verification

All tests pass: 36/36, 27/27, 28/28, 19/19, 25/25, 31/31.
New features verified: H1/M15/M5 detection, trade guard, spread guard,
persistent OFI (correct across cycles), order-block zones.
