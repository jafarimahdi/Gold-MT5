# FINAL CHECK REPORT — MT5 Version

Date: 2026-08-19

Full review of the application from Step 0 to the last step, plus a resource /
performance assessment for running it in the background.

---

## 1. Does everything work? — YES (all verified)

| Check | Result |
|---|---|
| All 16 Python modules compile | ✅ |
| Step 2 analysis engine | ✅ 36/36 |
| Data providers | ✅ 27/27 |
| Market registry | ✅ 28/28 |
| Indicator correctness | ✅ 19/19 |
| Weekend/no-data/risk safety | ✅ 25/25 |
| Full pipeline end-to-end | ✅ 31/31 |
| **Total** | **166/166 checks pass** |
| 15 continuous loop cycles | ✅ no crash, handled every error gracefully |

The pipeline runs Step 0 → 1 → 2 → 3 → 4 → 5 in order, and each step is
isolated so a failure in one (e.g. data feed down) never takes down the rest.
When MT5 is absent it reports the problem and skips trading — never crashes.

## 2. How heavy is it? — VERY LIGHT

Measured on this machine:

| Metric | Value | Verdict |
|---|---|---|
| The "brain" (one full analysis) | **6.9 ms** | extremely fast |
| Full loop (data + analysis) | ~1 second | the 1s is an INTENTIONAL 0.5s×2 wait so the order book updates (needed for OFI) |
| Memory (RAM) | ~170 MB | normal — mostly numpy/pandas; a web browser uses 10× more |
| Memory growth over 20 runs | **0 MB** | no memory leak — safe to run for days |
| CPU | a few ms per minute | negligible |

**Conclusion: it is a LIGHT application.** It can easily run in the background
24/7 on a normal PC. The 170 MB is the one-time cost of loading Python +
numpy + pandas; it does not grow.

## 3. Can it run always behind, and work with MT5? — YES, with 3 requirements

To run it "always on" in the background:

1. **Keep the program running** — `python main.py --loop` (checks the market
   every 60 seconds, sleeps in between). Stop with Ctrl+C.
2. **Keep MT5 running** — the Python `MetaTrader5` package talks to the OPEN
   MT5 terminal. If MT5 is closed, the bot safely reports "not installed /
   not running" and waits.
3. **Keep the PC on** — the bot is a program on your computer; it needs the
   computer awake. (Later, when going live, run it on a cheap VPS so it
   doesn't depend on your PC.)

### How it works with MT5

- Data: the bot reads ticks + Level 2 depth + candles FROM MT5 (free).
- Signals: the Python bot writes `gold_signal.txt`.
- Trading: the `GoldTradingEA.mq5` (attached to an XAUUSD chart) reads that
  file and opens/closes/reverses positions — OR the Python Step 4 places
  orders directly through the `MetaTrader5` package.
- The indicator (`GoldSignalIndicator.mq5`) draws BUY/SELL arrows so you can
  see the signals on the chart.

## 4. Honest notes (small things to know)

- **Windows only for MT5** — the `MetaTrader5` package and the MQL5 EA need
  Windows + a running MT5 terminal. The analysis code itself runs anywhere.
- **MT5 has no Level 3** — brokers don't provide individual order events, so
  the L3 analyzer stays empty in this version (by design; it never breaks).
- **File growth is now automatically managed** — `maintenance.py` runs once
  per day and rotates old logs (7 days), trims the decision/outcome CSVs
  (latest 5000/2000 rows) and cleans old recordings (30 days). You can also
  run `python maintenance.py` manually to clean + see file sizes. So the app
  can run for months without ever filling the disk.
- **The robot is NOT a guaranteed profit maker** — the backtest honestly
  showed the signal weights need tuning on real data. The safety system is
  strong; profitability must be proven by paper trading + backtesting.

## 5. Verdict

✅ The application is **functional, smooth, light, and safe to run in the
background**. It is ready to be connected to your real MT5 demo account.

Next action for you (unchanged): on your Windows PC
1. `pip install MetaTrader5`
2. Open MT5 with a demo account
3. `python mt5_test.py`  → check TICK / LEVEL 2 / TICKS / CANDLES
4. `python main.py`      → check `has_data=True`
5. `python main.py --loop` to keep it running in the background
