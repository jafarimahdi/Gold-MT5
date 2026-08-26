# Gold MT5 / Pepperstone-ready Trading System — v0.6.0

This repository contains the automated gold-trading application in:

```text
gold_trading_system_mt5/
```

## Start here

Read this file first:

```text
gold_trading_system_mt5/AI_HANDOFF.md
```

It is the authoritative handoff for another AI, developer or future chat. It explains the architecture, current configuration, tests, known limitations, broker setup, futures roadmap and continuation prompt.

Then read:

```text
gold_trading_system_mt5/README.md
gold_trading_system_mt5/PEPPERSTONE_SETUP.md
gold_trading_system_mt5/VERSION_NOTE.md
```

## Current focus

The package is prepared for a Pepperstone MT5 demo account. It preserves the MT5, Rithmic, Databento, replay and futures-analysis capabilities.

The exact Pepperstone gold symbol must be discovered locally. Run the read-only diagnostic from the application directory:

```powershell
python broker_diagnostic.py
```

Keep automatic trading disabled until the diagnostic and execution tests are complete:

```env
TRADING_ENABLED=0
EXECUTION_MODE=none
```

## Security

Do not commit:

```text
.env
venv/
__pycache__/
data runtime files
logs
API keys
passwords
```

The downloadable source package intentionally excludes the local virtual environment, local `.env`, runtime data and logs. Recreate the environment using `requirements.txt`.
