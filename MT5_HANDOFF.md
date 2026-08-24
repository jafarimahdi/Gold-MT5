# HANDOFF REPORT — Gold Trading System (MT5 Version)

> **Purpose of this file:** this is a self-contained handoff so a NEW chat can
> continue building the MT5-data version from exactly where we left off, with
> zero lost context. Read it fully first, then follow "What to do next".

---

## 1. What this project is

An automated gold (XAUUSD) trading robot in Python + MetaTrader 5:

```
STEP 0  config.py                 settings, .env loading
STEP 1  data_providers.py         data source (demo / rithmic / databento / mt5 / replay)
STEP 2  step2_market_analysis.py  THE BRAIN: 25+ signals (CVD, delta, footprint,
                                  L2 depth/OFI/microprice, L3 order events, ATR,
                                  BB, ADX, MACD, RSI, VWAP/POC, correlations,
                                  news sentiment, news-time state machine)
STEP 3  step3_ai_decision.py      Gemini AI -> BUY/SELL/HOLD + confidence %
STEP 4  step4_mt5_execution.py    MT5 execution (Python SDK path) + safety gates
STEP 5  step5_monitoring.py       position monitoring + loop
        mt5_signal_bridge.py      writes gold_signal.txt for the MQL5 EA/indicator
        mt5_ea/GoldTradingEA.mq5  MT5 Expert Advisor (auto open/close/reverse)
        mt5_ea/GoldSignalIndicator.mq5  MT5 indicator (draws arrows)
```

Safety nets (all implemented + tested): session gate (weekend/holiday),
stale-feed gate, news blackout gate, daily-loss/drawdown circuit breaker,
confidence gate, master switch `TRADING_ENABLED`.

## 2. TWO versions of the project exist (important!)

| Folder | Purpose | Data source |
|---|---|---|
| `gold_trading_system/` | **L3 version** (full futures order book) | Rithmic or Databento |
| `gold_trading_system_mt5/` | **MT5 version** (this handoff, FREE broker data) | MetaTrader 5 terminal |

The code is **identical** in both. The ONLY difference is `DATA_SOURCE` and
market symbols in `.env`. The user wants the MT5 version developed **separately
in a new chat**, and to keep the L3 version untouched in the old chat.

## 3. Key facts learned (do NOT re-litigate these — they cost a lot of time)

1. **Rithmic API is NOT free.** It costs ~$100/month + $25 connection fee +
   exchange fees + a conformance test. Rithmic's own email says "R|Protocol
   API is not available for Demos which have live market data." The user's
   demo account gets `rpCode 13 — permission denied` on API login — that is
   correct behaviour, not a bug. R|Trader Pro (the desktop app) is free; the
   API is paid.
2. **Correct Rithmic settings** (for reference, already working):
   `RITHMIC_SYSTEM=Rithmic Paper Trading`, `RITHMIC_URL=rprotocol.rithmic.com:443`
   (that's the "Chicago Area" gateway), symbol `GC`, exchange `COMEX`.
3. **Databento asks for a card** (for $125 free credits then pay-as-you-go).
   The user does NOT want to give a card, so we pivoted to MT5.
4. **MT5 gives: ticks (with buy/sell via flags 32/64), Level 2 depth
   (market_book_get), OHLCV candles. MT5 does NOT give Level 3 (individual
   order events)** — brokers don't publish that. So the L3 analyzer stays
   empty in the MT5 version (it degrades gracefully, doesn't break anything).
5. The user is a beginner — everything must be explained in **simple English,
   small steps**.
6. The user controls position size manually via the EA input `InpManualLots`
   (default 0.01). The EA does full auto: open, close, reverse.
7. The user's machine: Windows, Git Bash terminal, Python installed at
   C:\Python312, project at `C:\Users\Jafar\Documents\gold_trading_system`,
   uses a venv. In Git Bash use `python` (not `python3`), and
   `source venv/Scripts/activate` to activate the venv.

## 4. Current state of the MT5 version (all verified green)

- All 16 Python modules compile.
- Test suites (in `gold_trading_system_mt5/`):
  - `demo_step2.py` → 36/36 pass
  - `test_data_providers.py` → 27/27
  - `test_markets.py` → 28/28
  - `test_indicators_golden.py` → 19/19
  - `test_session_risk.py` → 25/25
  - `e2e_test.py` → 31/31
- `MT5Provider` (in `data_providers.py`) is implemented and mock-tested:
  reads `symbol_info_tick`, `market_book_get`, `copy_ticks_from`,
  `copy_rates_from_pos` and builds the Step-2 schema correctly.
- `mt5_test.py` exists — a standalone MT5 connection test (like rithmic_test.py).
- `.env` in the MT5 version is already set to `DATA_SOURCE=mt5`, symbols XAUUSD.
- One bug was FIXED during testing: `compute_moving_averages` crashed on <12
  candles (EMA) — now guarded.

## 5. What is DONE vs LEFT (the plan)

### DONE (in both versions)
Building the whole system, all 166+ automated checks, the two-provider data
layer, the market registry (futures GC ↔ CFD XAUUSD), safety nets, backtest
harness, MQL5 EA + indicator, guides (START_HERE.md, TOMORROW_STEPS.md,
paper_trade_checklist.md, PRE_OPERATION_AUDIT.md, CHANGES.md).

### LEFT — to finish the MT5 version in the NEW chat
1. Confirm MT5 data works on the user's machine: run `python mt5_test.py`
   (Windows + MT5 terminal running + demo account). Fix any issues.
2. Run `python main.py` with MT5 data — confirm `has_data=True` and the
   Level 2 section shows real numbers.
3. Guide the user to: install MT5 (if not done), demo account, compile the
   MQL5 indicator (watch-only) then the EA (auto-trade on demo).
4. Set `MT5_SIGNAL_FILE` in `.env` to the MT5 Common Files folder.
5. Add the Gemini API key so Step 3 makes real decisions (optional but
   required for actual trading).
6. Paper trade 2–4 weeks, backtest, then (only then) consider real money.

## 6. How the new chat should continue

**Step A:** The user uploads `gold_trading_system_mt5.zip` (extract it) AND
pastes the "New Chat Prompt" below.

**Step B:** The new chat should:
1. Verify the code works: `python demo_step2.py` → 36/36.
2. Ask the user to run `python mt5_test.py` on Windows (MT5 open + demo
   account) and paste the output.
3. Based on that output, fix the MT5 connection path or proceed to `main.py`.
4. Then walk the user through the MT5 indicator + EA install (steps already
   in TOMORROW_STEPS.md boxes 5–8 and START_HERE.md).
5. Keep everything in SIMPLE English, small steps, one at a time.

## 7. Files inside the zip (46 files)

Everything needed. Key files to read first in the new chat:
- `VERSION_NOTE.md` — the two-version explanation
- `README.md` — full overview + layout
- `START_HERE.md` — beginner guide
- `TOMORROW_STEPS.md` — 8-box action plan
- `mt5_test.py` — the MT5 connection test
- `.env` + `.env.example` — configuration
- `data_providers.py` — contains `MT5Provider` (new in this version)

## 8. Gotchas to remember in the new chat

- On the user's Windows/Git Bash: use `python` not `python3`; activate venv
  with `source venv/Scripts/activate`.
- `MetaTrader5` Python package only works on Windows with MT5 terminal running.
- The MT5 provider needs the MT5 terminal logged into a demo account.
- MT5 `market_book_get` returns tuples named `type, price, volume` where
  type 0 = bid side, type 1 = ask side.
- MT5 tick flags: 32 = BUY aggressor, 64 = SELL aggressor.
- XAUUSD has NO Level 3 — never promise L3 from MT5.
- The user does NOT want to pay for data right now and does NOT want to give
  Databento a card. MT5 data is the chosen free path.

---

## NEW CHAT PROMPT (paste this verbatim in the new chat)

> Continue building the "Gold Trading System (MT5 version)". I have uploaded
> `gold_trading_system_mt5.zip` — extract it first. Read `VERSION_NOTE.md`,
> `README.md`, and this handoff context:
>
> This is an automated gold (XAUUSD) trading robot. There are TWO versions:
> the L3 futures version (Rithmic/Databento) kept in another chat, and THIS
> MT5-data version which reads free data from the user's MetaTrader 5 terminal
> (ticks + Level 2 depth + candles; MT5 has no Level 3 — brokers don't provide
> it). The user is a beginner: use simple English and small steps.
>
> Current state: the entire system is built and tested (36/36, 27/27, 28/28,
> 19/19, 25/25, 31/31). `MT5Provider` in data_providers.py is implemented.
> `.env` is already set to DATA_SOURCE=mt5. Next step: the user runs
> `python mt5_test.py` on Windows (MT5 terminal open + demo account) and pastes
> the output; then we fix the connection or proceed to `python main.py`.
>
> Important constraints: (1) user won't pay for data or give Databento a card;
> (2) user controls position size via the EA input InpManualLots; the EA does
> full auto open/close/reverse; (3) user's machine uses `python` (not python3)
> and `source venv/Scripts/activate`; (4) keep going step by step until the
> bot runs on MT5 data and can auto-trade on a demo account.
