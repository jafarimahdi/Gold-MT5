# cTrader / cTrader Open API — Later Investigation

This project currently uses the MetaTrader 5 Python package and MQL5 EA. cTrader is a different platform and cannot be enabled by changing `DATA_SOURCE`.

## Decision rule

1. Test Pepperstone MT5 first with `broker_diagnostic.py`.
2. If the Pepperstone MT5 symbol still returns zero Level 2 book levels, record that result.
3. Only then decide whether cTrader is worthwhile.

## What cTrader would require

A cTrader implementation would need a separate provider and possibly a separate execution adapter using cTrader Open API. It requires:

- a cTrader account connected to Pepperstone;
- a cTrader Open API application;
- client ID and client secret;
- OAuth access/refresh token flow;
- account ID and broker environment;
- symbol/asset mapping;
- market-data subscription permissions;
- order, position and deal mapping;
- reconnect and rate-limit handling.

Never put these credentials in GitHub or in `AI_HANDOFF.md`.

## Level 2 caution

The existence of a Depth of Market window does not by itself guarantee a full centralized Level 2 order book. The diagnostic must confirm actual book updates, bid/ask levels, sizes and timestamps. Any cTrader data must be labelled according to what the API actually supplies.

## Planned files if approved later

```text
ctrader_provider.py
ctrader_execution.py
ctrader_auth.py
test_ctrader_provider.py
```

Until those files are implemented and tested, keep `DATA_SOURCE=mt5` or use one of the existing `demo`, `replay`, `rithmic` or `databento` providers.
