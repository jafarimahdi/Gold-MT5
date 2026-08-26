"""
run_all_tests.py
===============
Run all local tests that do not require a live broker connection.

This runner uses the individual test scripts' fake/synthetic data paths. The
real MT5 connection check remains separate: `python mt5_test.py`.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


TESTS = [
    "demo_step2.py",
    "test_data_providers.py",
    "test_markets.py",
    "test_indicators_golden.py",
    "test_session_risk.py",
    "test_key_rotation.py",
    "test_news.py",
    "test_python_execution.py",
    "test_reports.py",
    "e2e_test.py",
]


def main() -> int:
    root = Path(__file__).resolve().parent
    failed = []
    for name in TESTS:
        print("\n" + "=" * 72)
        print(f"RUNNING {name}")
        print("=" * 72)
        result = subprocess.run([sys.executable, name], cwd=root)
        if result.returncode != 0:
            failed.append(name)

    print("\n" + "=" * 72)
    if failed:
        print("FAILED TEST FILES:")
        for name in failed:
            print(f"  - {name}")
        return 1
    print(f"ALL {len(TESTS)} LOCAL TEST FILES PASSED")
    print("Live MT5 validation is separate: python mt5_test.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
