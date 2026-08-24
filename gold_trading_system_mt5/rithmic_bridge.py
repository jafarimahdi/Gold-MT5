"""
rithmic_bridge.py
=================
Bridge between Rithmic (R|API) and the Step-2 data pipeline.

Uses the community package `async-rithmic` (v1.6.x). This code is verified
against the INSTALLED package API:

    RithmicClient(user, password, system_name, app_name, app_version, url)
        - `url` is the Rithmic gateway (wss:// auto-prepended).
        - default paper-trading/live gateway: rprotocol.rithmic.com:443
        - events: on_tick (dict), on_order_book (PROTOBUF, not dict)
        - subscribe_to_market_data(symbol, exchange, data_type:int)
          data_type bits: 1 = trades, 2 = BBO, 4 = order book

Callbacks:
    on_tick        -> dict with trade_price, trade_size, aggressor (int 1=BUY 2=SELL)
    on_order_book  -> protobuf with repeated bid_price/size, ask_price/size,
                      update_type (int enum)

Before connecting:
    pip install async-rithmic
    Log into R|Trader Pro once and accept the market-data agreement.
    COMEX/CME market data must be enabled on your Rithmic account.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class AsyncRithmicBridge:
    """Runs the async_rithmic client in a background thread and feeds a provider."""

    def __init__(self, provider, creds: Dict[str, str]):
        self.provider = provider
        self.creds = creds
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._error: Optional[str] = None
        self._book_bids: Dict[float, float] = {}
        self._book_asks: Dict[float, float] = {}

    # -- lifecycle ------------------------------------------------------------
    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True,
                                        name="rithmic-bridge")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def wait_ready(self, timeout: float = 20.0) -> bool:
        return self._ready.wait(timeout)

    # -- asyncio side ---------------------------------------------------------
    def _redact(self, text: str) -> str:
        pw = self.creds.get("password", "")
        return text.replace(pw, "***") if pw else text

    def _run(self) -> None:
        try:
            asyncio.run(self._main())
        except Exception as exc:  # pragma: no cover
            self._error = self._redact(f"{type(exc).__name__}: {exc}")
            logger.error("Rithmic bridge failed: %s", self._error)

    async def _main(self) -> None:
        try:
            from async_rithmic import RithmicClient, DataType, SysInfraType
        except ImportError as exc:
            self._error = ("The 'async-rithmic' package could not be imported: "
                           f"{exc}. Run: pip install async-rithmic")
            logger.error(self._error)
            return

        url = self.creds.get("url") or "rprotocol.rithmic.com:443"

        client = RithmicClient(
            user=self.creds["username"],
            password=self.creds["password"],
            system_name=self.creds["system"],
            app_name=self.creds["app_name"],
            app_version=self.creds["app_version"],
            url=url,
        )

        # wire callbacks BEFORE connecting
        client.on_tick += self._on_tick
        client.on_order_book += self._on_order_book

        try:
            # data-only connection (ticker plant; no order routing needed)
            await client.connect(plants=[SysInfraType.TICKER_PLANT])
        except Exception as exc:
            self._error = self._redact(
                f"Rithmic connect failed: {type(exc).__name__}: {exc}")
            logger.error("%s", self._error)
            return

        symbol = self.creds.get("symbol", "GC")
        exchange = self.creds.get("exchange", "COMEX")
        try:
            security_code = await client.get_front_month_contract(symbol, exchange)
        except Exception as exc:
            self._error = f"could not resolve front-month contract: {exc}"
            logger.error(self._error)
            return

        logger.info("Rithmic bridge: streaming %s (%s/%s) via %s",
                    security_code, symbol, exchange, url)

        data_type = int(DataType.LAST_TRADE) | int(DataType.ORDER_BOOK)  # 5
        try:
            await client.subscribe_to_market_data(security_code, exchange,
                                                  data_type)
        except Exception as exc:
            self._error = f"subscribe failed: {type(exc).__name__}: {exc}"
            logger.error(self._error)
            return

        self._ready.set()
        logger.info("Rithmic bridge: subscribed, waiting for data ...")

        # keep running until stopped
        while not self._stop.is_set():
            await asyncio.sleep(0.2)

        try:
            await client.disconnect()
        except Exception:
            pass
        logger.info("Rithmic bridge: disconnected.")

    # -- callbacks ------------------------------------------------------------
    def _on_tick(self, data: Dict[str, Any]) -> None:
        """Handle a LAST_TRADE or BBO tick (dict from async_rithmic)."""
        try:
            dtype = int(data.get("data_type", 0))
        except (TypeError, ValueError):
            return
        if dtype != 1:            # 1 == LAST_TRADE (ignore BBO here)
            return
        try:
            price = float(data.get("trade_price", 0) or 0)
            size = float(data.get("trade_size", 0) or 0)
        except (TypeError, ValueError):
            return
        if price <= 0 or size <= 0:
            return
        agg = int(data.get("aggressor", 0) or 0)   # 1=BUY, 2=SELL
        side = "SELL" if agg == 2 else "BUY"
        self.provider.handle_trade(price, size, side)

    def _on_order_book(self, response) -> None:
        """Handle an order-book update (PROTOBUF in async_rithmic 1.6.x)."""
        try:
            from async_rithmic import protocol_buffers as pb
            UT = pb.order_book_pb2.OrderBook.UpdateType
            ut = int(response.update_type)
            if ut in (int(UT.CLEAR_ORDER_BOOK), int(UT.NO_BOOK)):
                self._book_bids.clear()
                self._book_asks.clear()
                return

            for px, sz in zip(response.bid_price, response.bid_size):
                px = float(px)
                if sz > 0:
                    self._book_bids[px] = float(sz)
                else:
                    self._book_bids.pop(px, None)
            for px, sz in zip(response.ask_price, response.ask_size):
                px = float(px)
                if sz > 0:
                    self._book_asks[px] = float(sz)
                else:
                    self._book_asks.pop(px, None)

            # publish the full book when the update set is complete
            if ut in (int(UT.SNAPSHOT_IMAGE), int(UT.END), int(UT.SOLO)):
                self.provider.handle_depth(dict(self._book_bids),
                                           dict(self._book_asks))
        except Exception as exc:  # pragma: no cover
            logger.debug("order book parse skipped: %s", exc)
