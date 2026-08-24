# ⚠️ REMEMBER — when the user switches brokers / wants better data

The user will come back later to:
1. Try ANOTHER broker to get better data (Level 2 depth / order book).
2. Ask for an update + full review of the whole application, with ALL the
   previous functions and abilities it must have.

When that happens:
- Re-run the full check: `python demo_step2.py`, `test_data_providers.py`,
  `test_markets.py`, `test_indicators_golden.py`, `test_session_risk.py`,
  `e2e_test.py` (166 checks total).
- Review the complete feature list (see IMPROVEMENTS.md + FINAL_CHECK_REPORT.md):
  * CVD, delta, buy/sell pressure, footprint
  * L2: microprice, depth imbalance, OFI, absorption (needs a broker with depth)
  * L3: order events (only on futures - Databento/Rithmic)
  * ATR, Bollinger, ADX, MACD, RSI, SMA/EMA
  * VWAP, POC, value area, OBV, A/D, z-score
  * multi-TF confirmation (H1/M15/M5 vs M1)
  * order blocks / supply-demand zones
  * macro (DXY/VIX/yields - only if data provided)
  * news sentiment + news-time state (QUIET/WARNING/BLACKOUT)
  * spread guard, cooldown, daily trade cap, daily-loss breaker, session gate
  * trailing stop (EA)
- If the new broker's gold symbol has a different name (e.g. GOLD, XAUUSD.i,
  XAUUSD#), update `.env`: MT5_SYMBOL / TRADING_SYMBOL / DATA_SYMBOL.
- If the new broker publishes Level 2 depth, the L2 signals activate
  automatically (the MT5Provider already reads market_book_get()).
- Keep the two versions straight:
  * gold_trading_system_mt5/ = MT5 CFD data (Level 2 only)
  * gold_trading_system/ = L3 futures version (Rithmic/Databento)

Current status (2026-08-19): Vantage Markets demo, symbol XAUUSD+, data works
(tick/candles); no depth/trades on this CFD feed (order flow approximated from
candles). All 166 checks pass.
