"""
test_news.py
============
Offline unit tests for news.py (the free headline fetcher).

Uses a fake `requests` so nothing hits the network. Verifies RSS parsing,
deduplication, caching, disabled mode, and the safe enrichment of the
market_data dict that main.py feeds into Step 2.

Usage:  python test_news.py
"""

import sys
import types
import urllib.parse
from types import SimpleNamespace

import news
import config

PASS, FAIL = [], []
check = lambda name, cond: (PASS if cond else FAIL).append(name)

SAMPLE_RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<title>"gold price" - Google News</title>
<item>
  <title>Gold surges to record high as war fears grow - Reuters</title>
  <pubDate>Fri, 21 Aug 2026 10:00:00 GMT</pubDate>
  <source>Reuters</source>
</item>
<item>
  <title>Fed signals rate cut, dollar weakens - CNBC</title>
  <pubDate>Fri, 21 Aug 2026 09:00:00 GMT</pubDate>
  <source>CNBC</source>
</item>
<item>
  <title>Gold surges to record high as war fears grow - Reuters</title>
  <pubDate>Fri, 21 Aug 2026 10:00:00 GMT</pubDate>
  <source>Reuters</source>
</item>
</channel></rss>
"""


class _FakeResp:
    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        pass


class _FakeRequests:
    def __init__(self):
        self.utils = SimpleNamespace(quote=urllib.parse.quote)
        self.calls = 0

    def get(self, url, timeout=None, headers=None):
        self.calls += 1
        return _FakeResp(SAMPLE_RSS)


def main():
    # ---- disabled mode -----------------------------------------------------
    config.NEWS_ENABLED = False
    check("disabled: fetch_headlines returns []", news.fetch_headlines() == [])
    d = {}
    news.enrich_market_news(d)
    check("disabled: enrich does nothing", d == {})

    # ---- enabled mode with a fake feed --------------------------------------
    config.NEWS_ENABLED = True
    config.NEWS_CACHE_MINUTES = 15
    config.NEWS_MAX_HEADLINES = 15
    config.NEWS_TIMEOUT = 8

    fake = _FakeRequests()
    real_requests = news.requests
    news.requests = fake
    try:
        # wipe caches so we really exercise the fetch path
        news._MEMO.clear()
        news._MEMO_LOADED = False
        try:
            p = news._cache_path()
            if p.exists():
                p.unlink()
        except OSError:
            pass

        heads = news.fetch_headlines()
        check("fetch returns headlines", len(heads) > 0)
        check("duplicates removed (2 unique)", len(heads) == 2)
        check("headline text parsed",
              any("Gold surges" in h for h in heads))

        # second call must come from the cache (no new HTTP request)
        before = fake.calls
        heads2 = news.fetch_headlines()
        check("second call is cached (no extra request)", fake.calls == before)
        check("cache returns same headlines", heads2 == heads)

        # enrich_market_news injects without clobbering existing fields
        data = {"news": {"fetch_calendar": True, "events": [{"title": "CPI"}]}}
        news.enrich_market_news(data)
        check("enrich adds headlines",
              data["news"].get("headlines") == heads)
        check("enrich keeps fetch_calendar",
              data["news"].get("fetch_calendar") is True)
        check("enrich keeps events", data["news"].get("events") == [{"title": "CPI"}])

        # existing headlines are NOT overwritten
        data2 = {"news": {"headlines": ["keep me"]}}
        news.enrich_market_news(data2)
        check("enrich respects existing headlines",
              data2["news"]["headlines"] == ["keep me"])
    finally:
        news.requests = real_requests
        config.NEWS_ENABLED = True

    # ---- report -----------------------------------------------------------
    print("\n" + "=" * 60)
    print("NEWS MODULE TEST RESULTS")
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
