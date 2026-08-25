"""
test_key_rotation.py
====================
Proves the multi-key rotation the user asked about:

    "one API key is out — what about the second or third key?"

Simulates 3 Gemini keys in 3 different projects:
  - keyA raises a per-DAY quota error (like a project that used its 1,500)
  - keyB answers normally
  - keyC should never be reached

Also verifies that an OLD state file (the buggy "blocked all day" format)
is IGNORED, so upgrading un-blocks keys immediately.

Usage:  python test_key_rotation.py
"""

import json
import sys
import time
from datetime import datetime, timezone
from types import SimpleNamespace

import config
import step3_ai_decision as s3
from step2_market_analysis import _synthetic_market_data, analyze_market

PASS, FAIL = [], []
check = lambda name, cond: (PASS if cond else FAIL).append(name)


# ---- a fake Gemini SDK: keyA is daily-exhausted, keyB works, keyC unused ----
class _FakeSDK:
    last_key = None

    @staticmethod
    def configure(api_key=None, **kw):
        _FakeSDK.last_key = api_key

    class GenerativeModel:
        def __init__(self, model):
            self.model = model

        def generate_content(self, prompt):
            key = _FakeSDK.last_key
            if key == "keyA":
                raise RuntimeError(
                    "429 RESOURCE_EXHAUSTED: You exceeded your current quota, "
                    "please check your plan and billing details. (keyA)")
            if key == "keyB":
                return SimpleNamespace(text='{"action": "BUY", "confidence": 80, '
                                           '"rationale": "keyB used: war risk bullish"}')
            return SimpleNamespace(text='{"action": "SELL", "confidence": 99, '
                                        '"rationale": "keyC used (unexpected)"}')


def _clean_state():
    p = s3._key_state_path()
    if p.exists():
        try:
            p.unlink()
        except OSError:
            pass


def main():
    # ---- setup: 3 keys in 3 different projects ------------------------------
    config.GEMINI_API_KEYS = ["keyA", "keyB", "keyC"]
    real_genai = s3.genai
    s3.genai = _FakeSDK
    _clean_state()

    try:
        snap = analyze_market(_synthetic_market_data())

        # ---- scenario 1: keyA daily-quota -> keyB must take over -------------
        d = s3.AIDecisionEngine().decide(snap)
        check("keyA out -> keyB took over (BUY)",
              d.action == "BUY" and d.confidence == 80.0)
        check("rationale came from keyB",
              "keyB used" in d.rationale)
        check("keyC was never used", "keyC" not in d.rationale)

        # keyA was paused in a cooldown (not killed for the day). State stores
        # only a hash, never the raw API key.
        check("keyA now in cooldown", s3._key_id("keyA") in s3._exhausted_keys())
        state_text = s3._key_state_path().read_text(encoding="utf-8")
        check("cooldown state does not store raw key", "keyA" not in state_text)

        # ---- scenario 2: old state file (all keys blocked all day) is ignored -
        today = datetime.now(timezone.utc).date().isoformat()
        s3._key_state_path().write_text(json.dumps({
            "date": today, "exhausted": ["keyA", "keyB", "keyC"],
        }), encoding="utf-8")
        check("OLD state file is ignored (keys unblocked)",
              s3._exhausted_keys() == [])

        # ---- scenario 3: all 3 keys daily-exhausted -> HOLD, no crash --------
        _FakeSDK.last_key = None
        config.GEMINI_API_KEYS = ["keyX", "keyY", "keyZ"]
        _clean_state()

        class _AllDead:
            @staticmethod
            def configure(api_key=None, **kw):
                pass

            class GenerativeModel:
                def __init__(self, model):
                    pass

                def generate_content(self, prompt):
                    raise RuntimeError(
                        "429 RESOURCE_EXHAUSTED: You exceeded your current quota")
        s3.genai = _AllDead
        d3 = s3.AIDecisionEngine().decide(snap)
        check("all keys dead -> HOLD (no crash)",
              d3.action == "HOLD" and d3.confidence == 0.0)

        # ---- scenario 4: per-minute limit -> next key immediately ----------
        class _MinuteLimit:
            last_key = None

            @staticmethod
            def configure(api_key=None, **kw):
                _MinuteLimit.last_key = api_key

            class GenerativeModel:
                def __init__(self, model):
                    self.model = model

                def generate_content(self, prompt):
                    if _MinuteLimit.last_key == "minuteA":
                        raise RuntimeError(
                            "429 RESOURCE_EXHAUSTED: per minute rate limit")
                    return SimpleNamespace(
                        text='{"action":"BUY","confidence":80,'
                             '"rationale":"minute-limit failover"}')

        config.GEMINI_API_KEYS = ["minuteA", "minuteB"]
        _clean_state()
        s3.genai = _MinuteLimit
        started = time.perf_counter()
        d4 = s3.AIDecisionEngine().decide(snap)
        elapsed = time.perf_counter() - started
        check("per-minute limit fails over immediately",
              d4.action == "BUY" and elapsed < 1.0)
        check("per-minute key is cooled down later",
              s3._key_id("minuteA") in s3._exhausted_keys())
    finally:
        s3.genai = real_genai
        _clean_state()
        config.GEMINI_API_KEYS = []

    # ---- report -----------------------------------------------------------
    print("\n" + "=" * 60)
    print("KEY ROTATION TEST RESULTS")
    print("=" * 60)
    for name in PASS:
        print(f"  PASS  {name}")
    for name in FAIL:
        print(f"  FAIL  {name}")
    print("-" * 60)
    print(f"  {len(PASS)}/{len(PASS) + len(FAIL)} checks passed")
    print("=" * 60)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
