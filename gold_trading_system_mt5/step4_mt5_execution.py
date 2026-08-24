"""
step4_mt5_execution.py
======================
STEP 4: EXECUTION (MetaTrader 5)

Executes a Step 3 Decision ONLY if confidence > AI_CONFIDENCE_THRESHOLD (70%).

NEWS-TIME BEHAVIOUR
-------------------
- news_state == BLACKOUT  -> refuse new entries (SKIPPED), regardless of signal.
- news_state == WARNING   -> allow but WIDEN the stop and SHRINK position size
                             (news volatility protection).

POSITION SIZING
---------------
Risk-based: lots = (equity * risk%) / (stop_distance * contract_size).
Falls back to config.LOT_SIZE when equity is unavailable.

The MetaTrader5 SDK only works on Windows with a running MT5 terminal, so all
MT5 calls are guarded: without the SDK this module safely reports PENDING.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Optional

try:
    import MetaTrader5 as mt5
except ImportError:  # pragma: no cover
    mt5 = None

import config

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Outcome of a Step 4 attempt."""
    status: str                 # "EXECUTED" | "DEFERRED" | "SKIPPED" | "ERROR" | "PENDING"
    reason: str = ""
    order_id: Optional[int] = None
    symbol: str = config.SYMBOL
    volume: float = 0.0
    price: float = 0.0
    sl: float = 0.0
    tp: float = 0.0
    timestamp: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat() if self.timestamp else None
        return d


class MT5Executor:
    """Sends orders to MetaTrader 5."""

    def __init__(self, symbol: Optional[str] = None):
        # Trade on the MT5 (CFD) market, NOT the futures data market.
        self.symbol = symbol or config.MT5_SYMBOL or config.SYMBOL
        self.magic = 234000  # unique id for this EA's orders

    # ------------------------------------------------------------------ #
    def execute(self, decision, snapshot) -> ExecutionResult:
        """Execute `decision` (from Step 3) using the Step 2 `snapshot`.

        This method is deliberately defensive because tests, integrations and
        future execution paths may call it directly rather than through
        ``main._safety_gates``. The master switch and basic snapshot validity
        must therefore be enforced here too.
        """
        now = datetime.now(timezone.utc)

        # --- gate 0: master kill switch ----------------------------------------
        # Do not rely only on main.py: a direct caller must never be able to
        # bypass TRADING_ENABLED=0 and reach mt5.order_send().
        if not getattr(config, "TRADING_ENABLED", True):
            logger.info("STEP 4: SKIPPED — trading disabled (TRADING_ENABLED=0).")
            return ExecutionResult(
                status="SKIPPED",
                reason="trading disabled (TRADING_ENABLED=0)",
                symbol=self.symbol, timestamp=now)

        # --- gate 0a: execution owner -----------------------------------------
        # Direct Python order placement is allowed only in python mode. In EA
        # mode the bridge is the only path allowed to produce an order signal.
        mode = getattr(config, "EXECUTION_MODE", "none")
        if mode != "python":
            logger.info("STEP 4: SKIPPED — Python executor disabled in %s mode.",
                        mode)
            return ExecutionResult(
                status="SKIPPED",
                reason=f"Python execution disabled (EXECUTION_MODE={mode})",
                symbol=self.symbol, timestamp=now)

        # --- gate 0b: valid market snapshot -----------------------------------
        # An empty/no-data snapshot must never be turned into a real order using
        # the fallback ATR and the current MT5 price.
        if snapshot is None or float(getattr(snapshot, "price", 0.0) or 0.0) <= 0:
            logger.info("STEP 4: SKIPPED — empty or invalid market snapshot.")
            return ExecutionResult(
                status="SKIPPED",
                reason="empty or invalid market snapshot",
                symbol=self.symbol, timestamp=now)

        # --- gate 1: confidence -------------------------------------------------
        if decision.confidence < config.AI_CONFIDENCE_THRESHOLD:
            logger.info("STEP 4: SKIPPED — confidence %.1f%% < %.0f%% "
                        "(decision: %s).", decision.confidence,
                        config.AI_CONFIDENCE_THRESHOLD, decision.action)
            return ExecutionResult(
                status="SKIPPED",
                reason=f"confidence {decision.confidence:.1f}% below threshold "
                       f"{config.AI_CONFIDENCE_THRESHOLD:.0f}%",
                symbol=self.symbol, timestamp=now)

        # --- gate 2: actionable direction ---------------------------------------
        if decision.action not in ("BUY", "SELL"):
            logger.info("STEP 4: SKIPPED — action is %s (not BUY/SELL).",
                        decision.action)
            return ExecutionResult(status="SKIPPED",
                                   reason=f"action '{decision.action}' not tradable",
                                   symbol=self.symbol, timestamp=now)

        # --- gate 3: NEWS-TIME BLACKOUT ------------------------------------------
        news_state = getattr(getattr(snapshot, "news", None), "news_state", "QUIET")
        if news_state == "BLACKOUT":
            mins = getattr(snapshot.news, "minutes_to_next_event", 0.0)
            logger.info("STEP 4: SKIPPED — news BLACKOUT (event in %.0f min). "
                        "No new entries during news.", mins)
            return ExecutionResult(
                status="SKIPPED",
                reason=f"news blackout — next event in {mins:.0f} min",
                symbol=self.symbol, timestamp=now)

        # --- gate 4: MT5 availability -------------------------------------------
        if mt5 is None:
            logger.warning("STEP 4: MetaTrader5 SDK not installed -> cannot "
                           "execute (Windows + MT5 terminal required).")
            return ExecutionResult(status="PENDING",
                                   reason="MetaTrader5 SDK not installed",
                                   symbol=self.symbol, timestamp=now)
        if not mt5.initialize():
            logger.error("STEP 4: mt5.initialize() failed: %s", mt5.last_error())
            return ExecutionResult(status="ERROR", reason="MT5 init failed",
                                   symbol=self.symbol, timestamp=now)

        try:
            return self._place_order(decision.action, snapshot, news_state)
        finally:
            mt5.shutdown()

    # ------------------------------------------------------------------ #
    def _account_equity(self) -> Optional[float]:
        """Current account equity from MT5, else config fallback."""
        try:
            info = mt5.account_info()
            if info is not None and getattr(info, "equity", None):
                return float(info.equity)
        except Exception:
            pass
        return config.ACCOUNT_EQUITY if config.ACCOUNT_EQUITY > 0 else None

    def compute_lot_size(self, equity: float, stop_distance: float,
                         risk_pct: Optional[float] = None) -> float:
        """Risk-based lot sizing.

        lots = (equity * risk%) / (stop_distance * contract_size)
        Rounded down to 2 decimals, clamped to [0.01, MAX_LOT_SIZE].
        """
        risk_pct = risk_pct if risk_pct is not None else config.RISK_PER_TRADE_PCT
        if stop_distance <= 0 or config.CONTRACT_SIZE <= 0:
            return config.LOT_SIZE
        risk_amount = equity * risk_pct / 100.0
        lots = risk_amount / (stop_distance * config.CONTRACT_SIZE)
        lots = max(0.01, min(lots, config.MAX_LOT_SIZE))
        return float(np_round2(lots))

    # ------------------------------------------------------------------ #
    def _calc_sl_tp(self, action: str, price: float, atr: float,
                    news_state: str) -> tuple:
        """SL/TP from ATR multiples; widened during news WARNING."""
        sl_mult = config.STOP_LOSS_ATR_MULT
        if news_state == "WARNING":
            sl_mult *= config.NEWS_WIDEN_STOP_MULT
        tp_mult = config.TAKE_PROFIT_ATR_MULT
        if action == "BUY":
            return price - sl_mult * atr, price + tp_mult * atr
        return price + sl_mult * atr, price - tp_mult * atr

    def _place_order(self, action: str, snapshot,
                     news_state: str) -> ExecutionResult:
        """Send a market order with SL/TP. (Runs only when MT5 is available.)"""
        now = datetime.now(timezone.utc)
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            return ExecutionResult(status="ERROR", reason="no tick data",
                                   symbol=self.symbol, timestamp=now)

        is_buy = action == "BUY"
        price = tick.ask if is_buy else tick.bid  # CFD price from MT5

        # futures <-> CFD basis check (warns if the two markets dislocate)
        try:
            from spread_monitor import monitor as spread_mon
            spread_mon.update(getattr(snapshot, "price", 0.0), price)
            if spread_mon.is_wide():
                logger.warning("STEP 4: futures/CFD basis is wide — %s",
                               spread_mon.report())
        except Exception:
            pass

        # Re-anchor the FUTURES ATR to the CFD price. ATR is a movement measure;
        # it must be expressed as % of price and re-applied to the trade market
        # so SL/TP reflect market movement, not the (different) futures price.
        src_atr = snapshot.volatility.atr if snapshot.volatility.atr > 0 else \
            price * 0.005  # 0.5% fallback
        src_price = getattr(snapshot, "price", 0.0) or price
        atr = src_atr * (price / src_price) if src_price > 0 else src_atr
        sl, tp = self._calc_sl_tp(action, price, atr, news_state)

        # --- position sizing ----------------------------------------------------
        equity = self._account_equity()
        stop_distance = abs(price - sl)
        lot_size = self.compute_lot_size(equity, stop_distance) \
            if equity else config.LOT_SIZE
        if news_state == "WARNING":
            lot_size = lot_size * config.NEWS_REDUCE_SIZE_PCT  # shrink during news
        lot_size = float(np_round2(lot_size))

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": lot_size,
            "type": mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 20,
            "magic": self.magic,
            "comment": "gold-trading-bot",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error("STEP 4: order_send failed retcode=%s",
                         getattr(result, "retcode", None))
            return ExecutionResult(status="ERROR",
                                   reason=f"order_send retcode={getattr(result, 'retcode', None)}",
                                   symbol=self.symbol, volume=lot_size,
                                   price=price, sl=sl, tp=tp, timestamp=now)

        logger.info("STEP 4: EXECUTED %s %s %.2f lots @ %.2f (SL %.2f / TP %.2f) "
                    "order=%s", action, self.symbol, lot_size, price, sl, tp,
                    result.order)
        return ExecutionResult(status="EXECUTED", order_id=result.order,
                               symbol=self.symbol, volume=lot_size,
                               price=price, sl=sl, tp=tp, timestamp=now)


def np_round2(value: float) -> float:
    """Round to 2 decimals without numpy dependency (MT5 lot convention)."""
    return float(round(value * 100.0) / 100.0)
