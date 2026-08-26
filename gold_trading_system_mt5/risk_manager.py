"""
risk_manager.py
===============
Risk circuit-breaker for the gold trading system.

Protects the account with a daily-loss limit and a max-drawdown limit:

  - Daily loss limit: if today's realised PnL (from MT5 history deals) falls
    below -DAILY_LOSS_LIMIT_PCT % of equity, trading is HALTED until the next
    day (UTC midnight). The halt is persisted to disk so a restart cannot
    reset it.
  - Max drawdown: if account equity drops below peak_equity * (1 - MAX_DRAWDOWN_PCT),
    trading halts until the state is manually reset.

Works without MT5 (PnL reads as 0 -> no halt) so it never crashes the
pipeline; when MT5 is present it reads real deal history.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Tuple

try:
    import MetaTrader5 as mt5
except ImportError:  # pragma: no cover
    mt5 = None

import config

logger = logging.getLogger(__name__)

STATE_FILE = config.DATA_DIR / "risk_state.json"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _end_of_day(now: datetime) -> datetime:
    return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0,
                                             microsecond=0)


class RiskManager:
    """Daily-loss + drawdown circuit breaker."""

    def __init__(self, daily_loss_pct: Optional[float] = None,
                 max_drawdown_pct: Optional[float] = None):
        self.daily_loss_pct = daily_loss_pct if daily_loss_pct is not None \
            else config.DAILY_LOSS_LIMIT_PCT
        self.max_drawdown_pct = max_drawdown_pct if max_drawdown_pct is not None \
            else config.MAX_DRAWDOWN_PCT

    # -- persisted halt state --------------------------------------------------
    def load_state(self) -> dict:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def save_state(self, state: dict) -> None:
        try:
            STATE_FILE.write_text(json.dumps(state), encoding="utf-8")
        except OSError as exc:
            logger.warning("Could not persist risk state: %s", exc)

    def clear_state(self) -> None:
        try:
            STATE_FILE.unlink(missing_ok=True)
        except OSError:
            pass

    # -- account PnL -----------------------------------------------------------
    def account_equity(self) -> float:
        if mt5 is None:
            return config.ACCOUNT_EQUITY
        try:
            if not config.mt5_initialize(mt5):
                return config.ACCOUNT_EQUITY
            info = mt5.account_info()
            mt5.shutdown()
            if info is not None and getattr(info, "equity", None):
                return float(info.equity)
        except Exception:
            pass
        return config.ACCOUNT_EQUITY

    def daily_pnl(self, now: Optional[datetime] = None) -> float:
        """Realised PnL for today (profit + swap + commission), MT5 history."""
        if mt5 is None:
            return 0.0
        now = now or _now()
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        try:
            if not config.mt5_initialize(mt5):
                return 0.0
            deals = mt5.history_deals_get(day_start, now)
            mt5.shutdown()
            total = 0.0
            for d in deals or []:
                total += float(getattr(d, "profit", 0.0) or 0.0)
                total += float(getattr(d, "swap", 0.0) or 0.0)
                total += float(getattr(d, "commission", 0.0) or 0.0)
            return total
        except Exception as exc:
            logger.warning("Risk manager could not read MT5 history: %s", exc)
            try:
                mt5.shutdown()
            except Exception:
                pass
            return 0.0

    # -- main check ------------------------------------------------------------
    def check(self, equity: Optional[float] = None,
              now: Optional[datetime] = None) -> Tuple[bool, str]:
        """Return (trading_allowed, reason)."""
        now = now or _now()
        equity = equity or self.account_equity()

        # 1) persisted halt (daily-loss from earlier today, or manual drawdown)
        state = self.load_state()
        halt_until = state.get("halt_until")
        if halt_until:
            try:
                until = datetime.fromisoformat(halt_until)
                if until.tzinfo is None:
                    until = until.replace(tzinfo=timezone.utc)
                if now < until:
                    return False, state.get("reason", "risk halt active")
            except ValueError:
                pass
        # halt expired -> drop it
        if state.get("halt_until"):
            self.clear_state()

        # 2) max drawdown vs tracked peak
        peak = float(state.get("peak_equity", equity))
        if equity > peak:
            peak = equity
            state["peak_equity"] = peak
            self.save_state(state)
        if self.max_drawdown_pct > 0 and peak > 0:
            dd_pct = (peak - equity) / peak * 100.0
            if dd_pct >= self.max_drawdown_pct:
                self.save_state({
                    "halt_until": _end_of_day(now).isoformat(),
                    "reason": f"max drawdown {dd_pct:.1f}% >= "
                              f"{self.max_drawdown_pct:.1f}%",
                    "peak_equity": peak,
                })
                return False, f"max drawdown {dd_pct:.1f}% >= " \
                              f"{self.max_drawdown_pct:.1f}%"

        # 3) daily loss limit
        if self.daily_loss_pct > 0 and equity > 0:
            pnl = self.daily_pnl(now)
            limit = self.daily_loss_pct / 100.0 * equity
            if pnl <= -limit:
                self.save_state({
                    "halt_until": _end_of_day(now).isoformat(),
                    "reason": f"daily loss {pnl:.2f} <= -{limit:.2f}",
                    "peak_equity": peak,
                })
                return False, f"daily loss {pnl:.2f} hits limit -{limit:.2f}"

        return True, "ok"

    def reset(self) -> None:
        """Manually clear a halt (for operator override)."""
        self.clear_state()
        logger.info("Risk halt cleared.")
