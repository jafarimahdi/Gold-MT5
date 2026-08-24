from setuptools import setup, find_packages


def _requirements() -> list:
    deps = []
    with open("requirements.txt", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                deps.append(line)
    return deps


setup(
    name="gold_trading_system",
    version="0.2.0",
    description="Automated gold (XAUUSD) trading pipeline: "
                "data -> analysis -> AI decision -> execution -> monitoring",
    packages=find_packages(),
    py_modules=[
        "config",
        "main",
        "markets",
        "session",
        "setup_markets",
        "data_providers",
        "risk_manager",
        "spread_monitor",
        "backtest",
        "step1_data_acquisition",
        "step2_market_analysis",
        "step3_ai_decision",
        "step4_mt5_execution",
        "step5_monitoring",
        "mt5_signal_bridge",
    ],
    install_requires=_requirements(),
    python_requires=">=3.9",
    entry_points={"console_scripts": ["gold-trading=main:main"]},
)
