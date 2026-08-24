# PRE-OPERATION AUDIT — Gold Trading System

**Date:** 2026-08-19 · **Scope:** final confirmation review of the whole system
(Step 0 → Step 5) before operation.

---

## 0. How this audit was done (honest disclosure)

This is a **single-agent adversarial self-review**. I do not have the ability
to call other AI models or external experts, and no such review happened — I
will not pretend otherwise. What was actually done:

1. Fresh re-read of every production module.
2. Full re-run of all **six** test suites (166 checks).
3. Static analysis: compile, warning-as-error import of every module, scan for
   bare `except`, hard-coded secrets, and stray TODO/NotImplemented markers.
4. State-hygiene check (no stale risk halts on disk).
5. Loop smoke test (2 full pipeline cycles without error).
6. Logic review of both MQL5 files (syntax reviewed; not compiled — see §3).

---

## 1. Verified — what is confirmed working

| # | Area | Evidence | Result |
|---|---|---|---|
| 1 | All 16 Python modules compile | `py_compile` | ✅ |
| 2 | All modules import with warnings-as-errors | import smoke test | ✅ |
| 3 | Step 2 analysis engine | `demo_step2.py` | ✅ 36/36 |
| 4 | Data-provider → Step 2 mapping (Rithmic/Databento shapes) | `test_data_providers.py` | ✅ 27/27 |
| 5 | Market/symbol recognition + price-agnostic SL/TP | `test_markets.py` | ✅ 28/28 |
| 6 | Indicator correctness (EMA/RSI/ATR/MACD/ADX golden) | `test_indicators_golden.py` | ✅ 19/19 |
| 7 | Weekend / no-data / risk resilience | `test_session_risk.py` | ✅ 25/25 |
| 8 | Full pipeline integration (mocked Gemini + MT5) | `e2e_test.py` | ✅ 31/31 |
| 9 | Continuous loop survives multiple cycles | loop smoke test | ✅ |
| 10 | No stale risk halt left on disk | state hygiene | ✅ |
| 11 | No hard-coded secrets, no bare `except` | static scan | ✅ |

**Total: 166/166 checks pass.**

### Safety nets confirmed present (defence-in-depth)

| Layer | Where | Blocks trading when |
|---|---|---|
| Session gate | `session.py` + `main.py` | weekend / holiday / daily break |
| Feed gate | providers heartbeat + `main.py` | Rithmic data stale or empty |
| News gate | `EconomicCalendar` + Step 4 + EA | inside news BLACKOUT window |
| Risk gate | `risk_manager.py` + `main.py` | daily loss / drawdown breach |
| Confidence gate | Step 4 + EA | AI confidence below threshold |
| EA re-enforcement | `GoldTradingEA.mq5` | same rules inside MT5 |

---

## 2. What was fixed during this final review

- Empty-feed crash in `analyze_tick_data()` (would have fired on a weekend
  Rithmic connection with no data).
- Empty feed misread as "oversold" (RSI defaulted to 0) — now returns
  NEUTRAL with **0% confidence**.
- `config.reload_env()` now truly re-binds settings and drops removed keys.
- `main.py` now re-reads `.env` every loop cycle.

---

## 3. NOT verifiable from this sandbox — you must verify these yourself

These cannot be tested here (no live credentials, no Windows/MT5, no network
to Rithmic). They are logic-reviewed but **unverified in operation**:

1. **Live Rithmic/Databento connection** — the transport seam
   (`RithmicProvider.connect()`) needs your actual SDK/wrapper/socket wired to
   `handle_depth()` / `handle_order_event()` / `handle_trade()`.
2. **MQL5 compilation** — `GoldTradingEA.mq5` and `GoldSignalIndicator.mq5`
   are reviewed but must be compiled in MetaEditor (F7); MT5 will flag any
   remaining syntax issue.
3. **Real MT5 execution** — order placement, SL/TP acceptance, symbol-specific
   tick size/lot-step constraints can only be confirmed against your broker.
4. **Real market behaviour** — spread, slippage, and whether the signal engine
   has any real edge (see §5).
5. **Economic-calendar live feed** — falls back to a curated offline calendar
   in this sandbox (no internet); verify it fetches live on your machine.

---

## 4. Known limitations & residual risks (read carefully)

1. **No proven edge.** The backtest on synthetic data is *negative*
   (≈ -3% return at 70% confidence, negative Sharpe). The signal weights are
   heuristic. **This system must not run with real money until it shows a
   positive expectancy on real recorded Rithmic data.**
2. **Single-instrument, single-direction-at-a-time logic.** The EA holds one
   net position; it is not a portfolio engine.
3. **Spot vs futures basis** is assumed stable; `spread_monitor.py` only warns,
   it does not halt (consider making a wide basis a hard gate later).
4. **News calendar is US-centric** and only covers scheduled events — flash
   geopolitical shocks are not modelled.
5. **Sentiment model is asset-agnostic** (e.g. "recession fears" reads negative
   though it is often bullish for gold).
6. **The EA path and the Python SDK path can both trade.** Use **one** of them,
   not both at once, or they may double-trade. (Recommendation: use the EA
   path only.)
7. **Risk manager reads MT5 history**; with MT5 unavailable it silently
   reports zero PnL (safe default, but verify it works with your terminal).

---

## 5. Verdict

### ✅ Cleared for: PAPER TRADING (MT5 demo + Rithmic demo)

The code is structurally sound, well-guarded, and extensively tested. It is
safe to run in **observation/demo mode**. Follow
[`paper_trade_checklist.md`](paper_trade_checklist.md) — it walks through
weekend/no-data checks first, then live-feed sanity, then demo auto-trading.

### ⛔ NOT cleared for: REAL MONEY

Three conditions must be met first:

1. **Record real Rithmic data** (`RECORD_DATA=1`) and **backtest** it until the
   signal engine shows positive expectancy (positive Sharpe / profit factor
   > 1) on out-of-sample data.
2. **Paper trade 2–4 weeks** on the MT5 demo with zero fatal incidents across
   every safety gate.
3. **Wire and verify the live Rithmic transport** (the one remaining TODO) and
   confirm the economic calendar fetches live events.

### The single most important sentence of this audit

> The system knows how to **stop** (session, feed, news, risk, confidence
> gates) — but it has not yet shown that it knows how to **win**. Operate it
> first as a watcher and a paper trader; treat any real-money deployment as a
> decision you make only after the backtest and paper-trade phases succeed.

---

*Audit performed by a single agent (no external AI consulted). All claims
above are reproducible from the workspace: run the six test suites + `backtest.py`
yourself to re-confirm.*
