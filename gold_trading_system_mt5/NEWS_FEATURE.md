# 📰 NEWS FEATURE — the bot now reads real news

## What changed

Before: the bot looked ONLY at charts (technical data). The Gemini AI did
not know about wars, Fed decisions, or inflation data.

Now: every 15 minutes the bot fetches the latest REAL headlines about:

1. **Gold price** (gold market news)
2. **Federal Reserve / interest rates** (central-bank news)
3. **War / geopolitics / world economy** (risk events)

...and hands them to Gemini together with the chart data. Gemini now has
clear instructions on how to weigh news:

| News | What Gemini is told |
|------|---------------------|
| War / geopolitical tension | safe-haven → gold usually goes UP |
| Fed hawkish / rate hikes / strong dollar | gold usually goes DOWN |
| Fed dovish / rate cuts / weak dollar | gold usually goes UP |
| High inflation / recession fears | gold usually goes UP (hedge) |
| Calm markets / strong stocks | neutral to DOWN |

## Where the news comes from

- **Google News RSS** — completely FREE, no API key, no card, no signup.
- **Economic calendar** — free ForexFactory calendar (scheduled events like
  FOMC, CPI, NFP). I also fixed its broken web address and made it fetch only
  once per hour (the free server blocks you if you ask every minute).

## Important safety facts

- If the internet is down or news fails to load, **the bot keeps working
  normally** — it just sees no headlines that cycle.
- News is **cached**, so we never spam the free news service.
- You can turn news OFF any time in `.env`: set `NEWS_ENABLED=0`.

## Settings you can change (in .env)

```
NEWS_ENABLED=1          # 1 = on, 0 = off
NEWS_CACHE_MINUTES=15   # how often to fetch fresh headlines
NEWS_MAX_HEADLINES=15   # how many headlines to give Gemini
NEWS_TIMEOUT=8          # seconds to wait for the news site
```

If a line is missing from `.env`, the default above is used — so you do NOT
have to add anything for news to work. It is ON by default.

## What to watch for

In the terminal you will now see a line like:

```
news: 15 fresh headlines fetched.
```

And the snapshot's NEWS section will show `Headlines: 15`.
Gemini's "rationale" (in the log) should now sometimes mention news
(e.g. "war risk supports gold, but hawkish Fed caps the upside").
