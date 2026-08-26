# MT5 Version Handoff

The authoritative project handoff is:

```text
gold_trading_system_mt5/AI_HANDOFF.md
```

Read that file first when moving this project to another chat, AI or developer. It contains the current architecture, configuration model, test history, known limitations, Pepperstone setup, futures roadmap, security rules and the prompt for continuation.

## Current package

This repository contains the MT5-data version of the Gold Trading System. It is prepared for a Pepperstone MT5 demo account, but the exact Pepperstone symbol must be discovered locally with:

```text
python broker_diagnostic.py
```

The current package preserves the futures/Rithmic/Databento providers and adds a Python execution foundation, broker diagnostics, signal expiry, modern Gemini SDK preference, immediate key failover, safer reporting and a clean handoff process.

Do not commit `.env`, `venv`, `__pycache__`, logs, generated data or credentials. Keep automatic trading disabled until the local broker diagnostic, EA/Python execution choice and demo tests are complete.
