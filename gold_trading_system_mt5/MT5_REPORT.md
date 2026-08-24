# MT5 VERSION — STATUS REPORT

Date: 2026-08-19 · Version: gold_trading_system_mt5 (Level 2, free MT5 broker data)

---

## 1. What is DONE (verified today — all tests green)

### The whole system is BUILT and TESTED
| Component | File | Tests |
|---|---|---|
| Analysis brain (25+ signals) | step2_market_analysis.py | 36/36 |
| Data providers (demo/rithmic/databento/mt5/replay) | data_providers.py | 27/27 |
| Market registry (futures↔CFD) | markets.py | 28/28 |
| Indicator correctness | test_indicators_golden.py | 19/19 |
| Weekend/no-data/risk safety | test_session_risk.py | 25/25 |
| Full pipeline integration | e2e_test.py | 31/31 |

**Total: 166 automated checks pass.**

### What works
- ✅ `MT5Provider` — reads your MT5 terminal: ticks (buy/sell side), Level 2
  depth (market_book_get), OHLCV candles (copy_rates_from_pos).
- ✅ `mt5_test.py` — standalone test to check your MT5 connection.
- ✅ `.env` already set: `DATA_SOURCE=mt5`, symbol XAUUSD.
- ✅ Safety nets: weekend gate, stale-feed gate, news blackout, daily-loss
  breaker, confidence gate, master switch (TRADING_ENABLED).
- ✅ MT5 Expert Advisor (`GoldTradingEA.mq5`) — full auto open/close/reverse,
  you control position size via `InpManualLots`.
- ✅ MT5 indicator (`GoldSignalIndicator.mq5`) — draws BUY/SELL arrows.
- ✅ Backtest harness, decision log, trade-outcome log, replay mode.
- ✅ Bug fixed during testing: EMA crash on fewer than 12 candles.

### Honest limitation (by design)
- ❌ MT5 gives NO Level 3 (individual order events). Brokers don't provide it.
  The Level-3 analyzer stays empty (degrades gracefully, never breaks).
- Everything else — CVD, footprint, L2 OFI, microprice, technicals, macro,
  news, signal — works fully from ticks + depth.

---

## 2. What is LEFT (in order)

### Phase A — First real data (do this next)
1. On Windows: `pip install MetaTrader5`
2. Open MetaTrader 5, log into a **demo** account, keep it running.
3. Run `python mt5_test.py` — expect TICK / LEVEL 2 / TICKS / CANDLES numbers.
   → paste output back if anything is wrong.
4. Run `python main.py` — expect `STEP 1 ... OK (mt5, ... has_data=True)`.

### Phase B — See signals on MT5 (watch only, no trading)
5. Set `MT5_SIGNAL_FILE` in `.env` to the MT5 Common Files folder.
6. Compile `GoldSignalIndicator.mq5` (MetaEditor F7), attach to XAUUSD chart.
   Green arrow = BUY, red = SELL.

### Phase C — Auto-trade on DEMO
7. Add `GEMINI_API_KEY=...` in `.env` (the AI brain; without it Step 3 always
   says HOLD so nothing trades).
8. Compile `GoldTradingEA.mq5`, attach to chart, set `InpManualLots` (e.g.
   0.01), enable AutoTrading.
9. Run `python main.py --loop` to keep it going (Ctrl+C to stop).

### Phase D — Before real money
10. Paper trade 2–4 weeks on demo.
11. `python backtest.py` — tune until profit factor > 1.
12. Only then consider real money.

---

## 3. Suggestions to make it better (advice)

### High value, easy (do these soon)
1. **Add the Gemini key + watch Step 3.** The AI decision is the brain — until
   the key is set, the robot never trades. Test it early.
2. **Use a VPS later.** When going live, run on a cheap VPS (or a PC that stays
   on 24/7) — the bot must keep running to trade.
3. **Start tiny.** `InpManualLots=0.01` on a demo for weeks before anything.

### Medium value (after it runs on demo)
4. **Record sessions + backtest.** Set `RECORD_DATA=1` to save real MT5 data,
   then `python backtest.py --replay data/record_*.json` — find out if the
   signals actually have an edge on real data.
5. **Tune the signal engine** with those results — the current weights are
   hand-picked and have NO proven edge yet (the honest backtest showed that).
6. **Test the news blackout on a live news day** — verify no trades open in the
   window. The news state machine is a key differentiator.

### Nice-to-have later
7. **Add a trailing stop** in the EA (Step 5 monitoring upgrade).
8. **Daily-loss breaker test** — simulate a losing day and confirm it halts.
9. **Multi-timeframe confirmation** (e.g. require M1 + M5 to agree) to filter
   noise — would improve precision.

---

## 4. IMPORTANT — the OTHER version (do not confuse)

There is a second project: `gold_trading_system/` = the **L3 version** (full
futures order book via Rithmic/Databento). When the user says "Level 3 data",
switch to that folder/chat — see `gold_trading_system/L3_REMINDER.md` there.

This MT5 version is Level 2 only.
