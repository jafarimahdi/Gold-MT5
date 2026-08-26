# Pepperstone MT5 Setup and Broker Check

This project is prepared to use Pepperstone through MetaTrader 5, but the exact Pepperstone symbol and terminal path must be confirmed on the user's account. Do not guess the symbol: brokers may use `XAUUSD`, `XAUUSD.`, `XAUUSD+`, `XAUUSD.a`, `GOLD`, or another suffix.

## Safe starting configuration

Use a local `.env` file, never commit it:

```env
BROKER_NAME=Pepperstone
DATA_SOURCE=mt5
MT5_LOGIN=0
MT5_SYMBOL=XAUUSD
TRADING_SYMBOL=XAUUSD
DATA_SYMBOL=XAUUSD
DATA_MARKET=XAUUSD
TRADE_MARKET=XAUUSD
MT5_TERMINAL_PATH=C:\Program Files\Pepperstone MetaTrader 5\terminal64.exe
TRADING_ENABLED=0
EXECUTION_MODE=python
```

`MT5_LOGIN=0` means the program uses the already-open Pepperstone MT5 terminal. If several MT5 terminals are installed, set `MT5_TERMINAL_PATH` to the intended `terminal64.exe` path.

## First check — read-only

1. Install and open Pepperstone MT5.
2. Log in to the Pepperstone demo account.
3. Add the gold symbol to Market Watch.
4. Confirm the exact symbol spelling.
5. From the application directory run:

```powershell
python broker_diagnostic.py
python mt5_test.py
```

Neither command places an order.

`broker_diagnostic.py` reports:

- selected symbol;
- bid/ask and last price;
- digits and point size;
- minimum, maximum and step volume;
- stops and freeze levels;
- supported filling information;
- Level 2 market-book level count;
- candidate gold symbols if the configured symbol is missing.

## Python execution test

Keep trading disabled for the first run:

```env
EXECUTION_MODE=python
TRADING_ENABLED=0
```

Run one pass:

```powershell
python main.py
```

Expected behavior:

- data is read from Pepperstone MT5;
- analysis and Gemini can run;
- Step 4 is skipped;
- the EA signal is neutralised;
- no order is sent.

## Explicit demo order plumbing test

This verifies broker order acceptance, not the strategy's decision quality. Use
only a Pepperstone demo account, keep the EA detached/AutoTrading disabled, and
make sure no XAUUSD position is open.

Set locally:

```env
EXECUTION_MODE=python
TRADING_ENABLED=1
MAX_LOT_SIZE=0.01
```

Then run exactly one side with explicit confirmation:

```powershell
python demo_order_test.py --side BUY --confirm-demo-order
```

The script opens at most the configured maximum volume, waits five seconds and
attempts to close only the bot-owned position. It does not use Gemini and is
not a strategy recommendation. If the open request fails, no close is
attempted. If interrupted after opening, close the bot position manually in
MT5.

Afterward immediately set:

```env
TRADING_ENABLED=0
```

## Controlled demo trading

Only after the read-only checks and Python execution tests pass:

1. Confirm the account is a demo account.
2. Set the smallest broker-supported volume.
3. Close or identify any existing manual positions.
4. Keep the EA detached or AutoTrading disabled.
5. Set `EXECUTION_MODE=python`.
6. Set `TRADING_ENABLED=1` only for a supervised test.
7. Run one pass, inspect the order result in MT5, then stop.
8. Test same-direction duplicate prevention and opposite-direction reversal.

Do not run Python execution and EA AutoTrading at the same time.

## Level 2 result

If the diagnostic shows zero book levels, Pepperstone MT5 is not providing usable market-book data for that symbol/terminal. The bot can still use price, candle and quote data, but order-flow fields should be labelled estimated.

If Level 2 is zero, record that result and use the preserved Rithmic/Databento futures providers when genuine Level 2/Level 3 order-flow is required. This package does not include another trading-platform integration.

## Changing broker later

For another MT5 broker, repeat this checklist and update only the local `.env` values:

- `BROKER_NAME`;
- exact `MT5_SYMBOL`;
- `TRADING_SYMBOL` and `DATA_SYMBOL`;
- login/server settings if not using the running terminal;
- `MT5_TERMINAL_PATH` if multiple terminals exist;
- `MT5_SIGNAL_FILE` only if EA mode is used.

The Python source, futures providers and analysis engine should remain unchanged.
