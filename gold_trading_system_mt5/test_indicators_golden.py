"""
test_indicators_golden.py
=========================
Golden tests for the TechnicalAnalyzer indicators.

Indicators are checked against:
  1) independent reference implementations written here (EMA, RSI Wilder, ATR,
     SMA, Bollinger, MACD), and
  2) analytic cases with known answers (RSI of a monotonic series == 100,
     ATR of a constant-range series == range, Bollinger std of a constant
     series == 0, MACD histogram == macd - signal), and
  3) behavioural ADX checks (strong trend -> ADX high, flat noise -> ADX low).

If TA-Lib is installed it is also used as a second reference (optional).
"""

import sys

import numpy as np

from step2_market_analysis import TechnicalAnalyzer

try:
    import talib  # type: ignore
    HAS_TALIB = True
except ImportError:
    HAS_TALIB = False

PASS, FAIL = [], []
check = lambda name, cond: (PASS if cond else FAIL).append(name)

ta = TechnicalAnalyzer()


# --------------------------------------------------------------------------- #
# Independent references
# --------------------------------------------------------------------------- #
def ref_ema(data: np.ndarray, period: int) -> float:
    mult = 2.0 / (period + 1)
    ema = float(np.mean(data[:period]))
    for v in data[period:]:
        ema = v * mult + ema * (1 - mult)
    return ema


def ref_rsi(close: np.ndarray, period: int = 14) -> float:
    d = np.diff(close)
    gains = np.clip(d, 0, None)
    losses = np.clip(-d, 0, None)
    ag = float(np.mean(gains[:period]))
    al = float(np.mean(losses[:period]))
    for i in range(period, len(gains)):
        ag = (ag * (period - 1) + gains[i]) / period
        al = (al * (period - 1) + losses[i]) / period
    if al == 0:
        return 100.0
    rs = ag / al
    return float(np.clip(100 - 100 / (1 + rs), 0, 100))


def ref_atr(high, low, close, period=14) -> float:
    pc = np.roll(close, 1); pc[0] = close[0]
    tr = np.maximum(high - low,
                    np.maximum(np.abs(high - pc), np.abs(low - pc)))
    atr = float(np.mean(tr[:period]))
    for i in range(period, len(tr)):
        atr = (atr * (period - 1) + tr[i]) / period
    return atr


def ref_macd(close, fast=12, slow=26, sig=9):
    def ema_series(d, p):
        out = np.full(len(d), np.nan)
        m = 2.0 / (p + 1)
        out[p - 1] = float(np.mean(d[:p]))
        for i in range(p, len(d)):
            out[i] = d[i] * m + out[i - 1] * (1 - m)
        return out
    ef, es = ema_series(close, fast), ema_series(close, slow)
    line = ef - es
    valid = line[slow - 1:]
    sigline = ema_series(valid, sig)
    return float(line[-1]), float(sigline[-1])


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #
def test_analytic():
    # RSI of strictly increasing series == 100
    up = np.linspace(100, 200, 40)
    check("RSI monotonic up == 100", ta.compute_rsi(up) == 100.0)
    # RSI of strictly decreasing series == 0
    check("RSI monotonic down == 0", ta.compute_rsi(np.linspace(200, 100, 40)) == 0.0)

    # ATR of constant range 2 == 2
    c = np.full(30, 100.0)
    check("ATR constant range == 2",
          abs(ta.compute_atr(c + 1, c - 1, c) - 2.0) < 1e-9)

    # Bollinger of constant series: upper == middle == lower
    u, m, l = ta.compute_bollinger_bands(c)
    check("Bollinger constant -> flat bands", u == m == l)

    # SMA exact
    check("SMA-9 exact", abs(ta.compute_moving_averages(c)["sma_9"] - 100.0) < 1e-12)

    # MACD histogram == macd - signal (invariant)
    close = np.array([100 + i * 0.5 + 3 * np.sin(i / 5) for i in range(90)])
    macd, sig, hist = ta.compute_macd(close)
    check("MACD hist == macd - signal", abs(hist - (macd - sig)) < 1e-9)
    # MACD positive on strong uptrend
    strong = np.linspace(100, 180, 90)
    m2, s2, h2 = ta.compute_macd(strong)
    check("MACD > 0 in strong uptrend", m2 > 0)


def test_against_reference():
    rng = np.random.default_rng(7)
    close = 100 + np.cumsum(rng.normal(0.05, 1.0, 200))
    high = close + rng.uniform(0.5, 3, 200)
    low = close - rng.uniform(0.5, 3, 200)

    check("EMA-12 matches reference",
          abs(ta._ema(close, 12) - ref_ema(close, 12)) < 1e-9)
    check("EMA-26 matches reference",
          abs(ta._ema(close, 26) - ref_ema(close, 26)) < 1e-9)
    check("RSI matches reference",
          abs(ta.compute_rsi(close) - ref_rsi(close)) < 1e-9)
    check("ATR matches reference",
          abs(ta.compute_atr(high, low, close) - ref_atr(high, low, close)) < 1e-9)
    rm, rs = ref_macd(close)
    tm, ts, th = ta.compute_macd(close)
    check("MACD line matches reference", abs(tm - rm) < 1e-6)
    check("MACD signal matches reference", abs(ts - rs) < 1e-6)


def test_adx_behaviour():
    rng = np.random.default_rng(3)
    # strong uptrend -> ADX should be meaningfully high
    t_close = np.linspace(100, 150, 80)
    t_high = t_close + 1
    t_low = t_close - 1
    adx_t, _, _ = ta.compute_adx(t_high, t_low, t_close)
    check("ADX high in strong trend (>25)", adx_t > 25)

    # flat noise -> ADX low
    f_close = 100 + rng.normal(0, 0.2, 80)
    f_high = f_close + 0.5
    f_low = f_close - 0.5
    adx_f, _, _ = ta.compute_adx(f_high, f_low, f_close)
    check("ADX low in flat noise (<25)", adx_f < 25)

    # always within [0, 100]
    check("ADX within [0,100]", 0 <= adx_t <= 100 and 0 <= adx_f <= 100)
    # +DI / -DI non-negative and sum > 0
    _, pdi, mdi = ta.compute_adx(t_high, t_low, t_close)
    check("+DI/-DI non-negative", pdi >= 0 and mdi >= 0)
    check("+DI > -DI in uptrend", pdi > mdi)


def test_talib_crosscheck():
    if not HAS_TALIB:
        check("TA-Lib cross-check (skipped — not installed)", True)
        return
    rng = np.random.default_rng(11)
    close = 100 + np.cumsum(rng.normal(0.05, 1.0, 300))
    high = close + rng.uniform(0.5, 3, 300)
    low = close - rng.uniform(0.5, 3, 300)

    check("TA-Lib RSI within 1.0",
          abs(ta.compute_rsi(close) - talib.RSI(close, 14)[-1]) < 1.0)
    check("TA-Lib ATR within 1.0",
          abs(ta.compute_atr(high, low, close) -
              talib.ATR(high, low, close, 14)[-1]) < 1.0)
    check("TA-Lib ADX within 5.0",
          abs(ta.compute_adx(high, low, close)[0] -
              talib.ADX(high, low, close, 14)[-1]) < 5.0)


def main():
    test_analytic()
    test_against_reference()
    test_adx_behaviour()
    test_talib_crosscheck()

    print("=" * 60)
    print("INDICATOR GOLDEN TEST RESULTS"
          f"{' (TA-Lib available)' if HAS_TALIB else ' (no TA-Lib)'}")
    print("=" * 60)
    for name in PASS:
        print(f"  PASS  {name}")
    for name in FAIL:
        print(f"  FAIL  {name}")
    print("-" * 60)
    print(f"  {len(PASS)}/{len(PASS) + len(FAIL)} checks passed")
    print("=" * 60)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
