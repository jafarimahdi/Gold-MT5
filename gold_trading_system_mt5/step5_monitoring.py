"""
step5_monitoring.py
===================
STEP 5: MONITORING & LOOP

Tracks open trades and drives the continuous loop back to Step 2.

`single_pass()` reports open positions (requires MT5; safe no-op otherwise).
`run_loop()` repeatedly calls a caller-supplied pipeline function (e.g.
main.run_pipeline) on a fixed interval.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Callable, List, Optional

try:
    import MetaTrader5 as mt5
except ImportError:  # pragma: no cover
    mt5 = None

import config

logger = logging.getLogger(__name__)


class TradeMonitor:
    """Monitors open trades and re-runs the pipeline in a loop."""

    def __init__(self, poll_seconds: Optional[int] = None):
        self.poll_seconds = (config.MONITOR_POLL_SECONDS if poll_seconds is None
                             else poll_seconds)

    # ------------------------------------------------------------------ #
    def check_open_trades(self) -> List[dict]:
        """Return open positions (empty list when MT5 unavailable)."""
        if mt5 is None:
            logger.info("STEP 5: MetaTrader5 SDK not installed -> no live "
                        "positions to monitor (demo mode).")
            return []
        if not config.mt5_initialize(mt5):
            logger.error("STEP 5: mt5.initialize() failed")
            return []
        try:
            positions = mt5.positions_get()
            mt5.shutdown()
            out = []
            for pos in positions or []:
                out.append({
                    "ticket": pos.ticket, "symbol": pos.symbol,
                    "type": "BUY" if pos.type == mt5.POSITION_TYPE_BUY else "SELL",
                    "volume": pos.volume, "price_open": pos.price_open,
                    "sl": pos.sl, "tp": pos.tp, "profit": pos.profit,
                })
            return out
        except Exception:
            logger.exception("STEP 5: position query failed")
            return []

    # ------------------------------------------------------------------ #
    def check_closed_deals(self, since: Optional[datetime] = None) -> List[dict]:
        """Return today's closed deals (for PnL logging / risk tracking).

        Empty when MT5 is unavailable — never raises.
        """
        if mt5 is None:
            return []
        since = since or datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0)
        try:
            if not config.mt5_initialize(mt5):
                return []
            deals = mt5.history_deals_get(since, datetime.now(timezone.utc))
            mt5.shutdown()
            out = []
            for d in deals or []:
                entry = getattr(d, "entry", None)
                if entry != 1:            # DEAL_ENTRY_OUT == 1
                    continue
                out.append({
                    # `ticket` is the unique MT5 deal ID. Keep it separate
                    # from position_id because one position can have more
                    # than one deal (partial closes, reversals, etc.).
                    "deal_id": getattr(d, "ticket", None),
                    "position_id": getattr(d, "position_id", getattr(d, "ticket", None)),
                    "symbol": getattr(d, "symbol", ""),
                    "type": "BUY" if getattr(d, "type", 1) == 0 else "SELL",
                    "price": float(getattr(d, "price", 0.0) or 0.0),
                    "pnl": round(float(getattr(d, "profit", 0.0) or 0.0)
                                 + float(getattr(d, "swap", 0.0) or 0.0)
                                 + float(getattr(d, "commission", 0.0) or 0.0), 2),
                })
            return out
        except Exception as exc:
            logger.warning("STEP 5: closed-deal query failed: %s", exc)
            try:
                mt5.shutdown()
            except Exception:
                pass
            return []

    # ------------------------------------------------------------------ #
    def single_pass(self) -> None:
        """One monitoring pass (used by main.py)."""
        positions = self.check_open_trades()
        if positions:
            for p in positions:
                logger.info("STEP 5: open %s %s %s @ %s (profit %s)",
                            p["type"], p["symbol"], p["volume"],
                            p["price_open"], p["profit"])
        else:
            logger.info("STEP 5: no open trades.")

    # ------------------------------------------------------------------ #
    def run_loop(self, pipeline_fn: Callable[[], None],
                 max_iterations: Optional[int] = None) -> None:
        """Run pipeline_fn every poll_seconds; Ctrl-C to stop.

        pipeline_fn is typically main.run_pipeline.
        """
        iteration = 0
        logger.info("STEP 5: starting monitoring loop "
                    "(every %ds). Ctrl-C to stop.", self.poll_seconds)
        try:
            while max_iterations is None or iteration < max_iterations:
                iteration += 1
                logger.info("STEP 5: --- loop iteration %d ---", iteration)
                pipeline_fn()
                time.sleep(self.poll_seconds)
        except KeyboardInterrupt:
            logger.info("STEP 5: loop stopped by user.")
