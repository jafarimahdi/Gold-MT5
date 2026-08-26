"""
robot_report.py
===============
The robot's "doctor" — one command that reads ALL the files and data the
robot saves, and prints ONE easy report of how the robot is working.

It checks:
  1. ACTIVITY         - how many decisions, date range, busiest day
  2. WHAT IT THOUGHT  - BUY/SELL/NEUTRAL, how often the AI was asked, news states
  3. TRADES & MONEY   - win rate, profit factor, total PnL, avg win/loss
  4. SYSTEM HEALTH    - file sizes, log errors/warnings, AI calls today, keys
  5. HISTORY/BACKTEST - downloaded history files + backtest results
  6. VERDICT          - plain-language advice

Usage:
    python robot_report.py            -> everything so far
    python robot_report.py --days 1   -> today only
    python robot_report.py --days 3   -> last 3 days
    python robot_report.py --days 7   -> last week
    python robot_report.py --days 30  -> last month
    (--days accepts ANY number: 1, 2, 3, 4, 5, 10, 30, ...)
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import config

DATA = config.DATA_DIR
LOGS = config.LOGS_DIR
BAR = "=" * 66


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def _read_csv(path: Path) -> list:
    if not path.exists():
        return []
    try:
        with open(path, "r", newline="", encoding="utf-8") as fh:
            return list(csv.DictReader(fh))
    except Exception:
        return []


def _dedupe_outcomes(rows: list) -> list:
    """Hide legacy duplicate outcome rows from reports.

    New rows are protected by the logger's deal-ID state. This report-level
    guard also keeps older CSV duplication from inflating the displayed stats.
    """
    seen = set()
    out = []
    fields = ("order_id", "symbol", "side", "pnl", "exit_price")
    for row in rows:
        key = tuple((row.get(k) or "").strip() for k in fields)
        if any(key) and key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def _recent(rows: list, days: int) -> list:
    """Keep rows whose timestamp is within the last `days` days (0 = all)."""
    if days <= 0:
        return rows
    cutoff = datetime.now() - timedelta(days=days)
    out = []
    for r in rows:
        ts = (r.get("timestamp") or "").strip()
        if not ts:
            out.append(r)
            continue
        try:
            if datetime.fromisoformat(ts) >= cutoff:
                out.append(r)
        except ValueError:
            out.append(r)
    return out


def _f(v, nd: int = 2):
    try:
        return round(float(v), nd)
    except (TypeError, ValueError):
        return 0.0


def _bar(values, width: int = 30) -> str:
    """A tiny ASCII bar chart of a list of numbers."""
    if not values:
        return ""
    mx = max(values) or 1
    return "".join("#" if v else "." for v in
                   [int(round(v / mx * width)) for v in values])


# --------------------------------------------------------------------------- #
# Section builders
# --------------------------------------------------------------------------- #
def _section_activity(rows, days):
    print("\n[1] ACTIVITY  (data/decisions_log.csv)")
    if not rows:
        print("    No decisions logged yet. The robot has not written any "
              "analysis rows.")
        return {}
    stamps = []
    per_day = Counter()
    for r in rows:
        ts = (r.get("timestamp") or "").strip()
        if ts:
            stamps.append(ts)
            per_day[ts[:10]] += 1
    stamps.sort()
    print(f"    Decisions logged : {len(rows)}")
    if stamps:
        print(f"    First / last     : {stamps[0][:16]}  ->  {stamps[-1][:16]}")
    if per_day:
        days_list = sorted(per_day)
        counts = [per_day[d] for d in days_list]
        busiest = days_list[counts.index(max(counts))]
        print(f"    Busiest day      : {busiest}  ({per_day[busiest]} decisions)")
        if len(days_list) > 1:
            print(f"    Per-day pattern  : {_bar(counts)}")
    return {"n": len(rows)}


def _section_daily(rows, outcomes):
    print("\n[2] DAY-BY-DAY  (improvement check — compare one day to the next)")
    if not rows and not outcomes:
        print("    (no data yet)")
        return
    dec_by_day = defaultdict(list)
    for r in rows:
        ts = (r.get("timestamp") or "").strip()
        if ts:
            dec_by_day[ts[:10]].append(r)
    out_by_day = defaultdict(list)
    for r in outcomes:
        ts = (r.get("timestamp") or "").strip()
        if ts:
            out_by_day[ts[:10]].append(r)

    all_days = sorted(set(dec_by_day) | set(out_by_day))
    gate = getattr(config, "AI_MIN_SIGNAL_STRENGTH", 10.0)
    print(f"    {'Date':<11}{'Decis':>6}{'AvgStr':>7}{'AI ask':>7}"
          f"{'AI B/S/H':>9}{'Trades':>7}{'PnL':>9}{'Win%':>6}")
    print("    " + "-" * 58)
    for d in all_days:
        decs = dec_by_day.get(d, [])
        outs = out_by_day.get(d, [])
        strengths = [_f(r.get("signal_strength")) for r in decs]
        avg_s = sum(strengths) / len(strengths) if strengths else 0.0
        asked = sum(1 for r in decs if _f(r.get("signal_strength")) >= gate)
        ai = Counter(r.get("ai_action", "?") or "?" for r in decs)
        ai_s = f"{ai.get('BUY', 0)}/{ai.get('SELL', 0)}/{ai.get('HOLD', 0)}"
        pnls = [_f(r.get("pnl")) for r in outs]
        wins = sum(1 for p in pnls if p > 0)
        wr = (100.0 * wins / len(pnls)) if pnls else None
        wr_s = f"{wr:.0f}" if wr is not None else "-"
        pnl_s = f"{sum(pnls):+.2f}" if pnls else "-"
        print(f"    {d:<11}{len(decs):>6}{avg_s:>7.1f}{asked:>7}"
              f"{ai_s:>9}{len(outs):>7}{pnl_s:>9}{wr_s:>6}")
    print("    (Decis = decisions logged, AvgStr = average signal strength,")
    print("     AI ask = times Gemini was consulted, Trades = closed trades,")
    print("     PnL = profit/loss in points, Win% = winning trades)")


def _section_thought(rows, days):
    print("\n[3] WHAT THE ROBOT THOUGHT")
    if not rows:
        print("    (no data)")
        return
    direction = Counter(r.get("signal_direction", "?") or "?" for r in rows)
    strengths = [_f(r.get("signal_strength")) for r in rows]
    confs = [_f(r.get("signal_confidence")) for r in rows]

    ai_actions = Counter(r.get("ai_action", "?") or "?" for r in rows)
    ai_conf = [_f(r.get("ai_confidence")) for r in rows
               if _f(r.get("ai_confidence")) > 0]
    gate = getattr(config, "AI_MIN_SIGNAL_STRENGTH", 10.0)
    asked = sum(1 for r in rows if _f(r.get("signal_strength")) >= gate)

    news = Counter(r.get("news_state", "?") or "?" for r in rows)
    regimes = Counter(r.get("regime", "?") or "?" for r in rows)
    execs = Counter(r.get("exec_status", "?") or "?" for r in rows)

    print(f"    Technical signal : BUY {direction.get('BUY',0)}   "
          f"SELL {direction.get('SELL',0)}   "
          f"NEUTRAL {direction.get('NEUTRAL',0)}")
    if strengths:
        print(f"    Avg strength     : {sum(strengths)/len(strengths):.1f} / 100")
    if confs:
        print(f"    Avg confidence   : {sum(confs)/len(confs):.1f} / 100")
    print(f"    AI (Gemini) asked: {asked} times  "
          f"(only when strength >= {gate:.0f})")
    if ai_actions:
        print(f"    AI answers       : BUY {ai_actions.get('BUY',0)}   "
              f"SELL {ai_actions.get('SELL',0)}   HOLD {ai_actions.get('HOLD',0)}")
    if ai_conf:
        print(f"    Avg AI confidence: {sum(ai_conf)/len(ai_conf):.1f}%")
    if news:
        print(f"    News states      : "
              + ", ".join(f"{k} {v}" for k, v in news.most_common()))
    if regimes:
        print(f"    Market regimes   : "
              + ", ".join(f"{k} {v}" for k, v in regimes.most_common()))
    if execs:
        print(f"    Executions       : "
              + ", ".join(f"{k} {v}" for k, v in execs.most_common()))


def _section_trades(rows, days):
    print("\n[4] TRADES & MONEY  (data/trade_outcomes.csv)")
    if not rows:
        print("    No closed trades yet. (The robot opens a trade only when the")
        print("    AI is >=70% sure — wait a few days and check again.)")
        return None
    pnls = [_f(r.get("pnl")) for r in rows]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    total = sum(pnls)
    wr = 100.0 * len(wins) / len(rows)
    pf = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else None

    print(f"    Closed trades    : {len(rows)}")
    print(f"    Win rate         : {wr:.1f}%   ({len(wins)}W / {len(losses)}L)")
    print(f"    Total PnL        : {total:+.2f}")
    if pf is not None:
        print(f"    Profit factor    : {pf:.2f}   (above 1.0 = winning robot)")
    if wins:
        print(f"    Average win      : {sum(wins)/len(wins):+.2f}")
    if losses:
        print(f"    Average loss     : {sum(losses)/len(losses):+.2f}")

    sides = defaultdict(lambda: [0, 0, 0.0])
    for r in rows:
        s = r.get("side", "?") or "?"
        p = _f(r.get("pnl"))
        sides[s][0] += 1
        if p > 0:
            sides[s][1] += 1
        sides[s][2] += p
    if sides:
        print("    By side:")
        for s, (n, w, p) in sorted(sides.items()):
            print(f"        {s:<6} {n} trades, {w} wins, PnL {p:+.2f}")
    return {"pf": pf, "n": len(rows), "wr": wr}


def _section_health(days):
    print("\n[5] SYSTEM HEALTH")
    data_files = [f for f in DATA.glob("*") if f.is_file()]
    log_files = [f for f in LOGS.glob("trading_*.log") if f.is_file()]
    total = sum(f.stat().st_size for f in data_files + log_files)
    print(f"    Data files       : {len(data_files)}  ({total/1024:.0f} KB total)")

    # log errors / warnings in the period
    err = warn = lines = 0
    cutoff = datetime.now() - timedelta(days=max(days, 7))
    for f in log_files:
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime < cutoff:
                continue
            for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
                lines += 1
                if " ERROR " in line or " ERROR[" in line:
                    err += 1
                elif " WARNING " in line:
                    warn += 1
        except OSError:
            continue
    print(f"    Log lines (7d)   : {lines}")
    print(f"    Errors   (7d)    : {err}")
    print(f"    Warnings (7d)    : {warn}")

    ai_calls = 0
    try:
        p = DATA / "ai_calls.json"
        if p.exists():
            st = json.loads(p.read_text(encoding="utf-8"))
            if st.get("date") == datetime.now().date().isoformat():
                ai_calls = int(st.get("calls", 0) or 0)
    except (json.JSONDecodeError, OSError):
        pass
    print(f"    AI calls today   : {ai_calls}  (cap {config.AI_MAX_CALLS_PER_DAY})")

    cooldown = 0
    try:
        p = DATA / "gemini_keys_state.json"
        if p.exists():
            st = json.loads(p.read_text(encoding="utf-8"))
            cooldown = len(st.get("cooldowns") or {})
    except (json.JSONDecodeError, OSError):
        pass
    print(f"    Gemini keys paused: {cooldown}")

    try:
        p = DATA / "market_snapshot.json"
        if p.exists():
            s = json.loads(p.read_text(encoding="utf-8"))
            print(f"    Last seen        : price {_f(s.get('price')):,.2f}   "
                  f"{s.get('signal_direction','?')} "
                  f"(strength {_f(s.get('signal_strength'),1)})   "
                  f"regime {s.get('regime','?')}")
    except (json.JSONDecodeError, OSError):
        pass


def _section_history(days):
    print("\n[6] HISTORY & BACKTEST")
    hist = sorted(DATA.glob("history_*.npz"))
    if hist:
        for h in hist:
            print(f"    {h.name:<40} {h.stat().st_size/1024:6.0f} KB")
    else:
        print("    No history downloaded yet. (Run:  python history_download.py)")

    try:
        p = DATA / "backtest_report.json"
        if p.exists():
            r = json.loads(p.read_text(encoding="utf-8"))
            print(f"    Backtest         : {r.get('n_trades','?')} trades, "
                  f"win rate {r.get('win_rate','?')}%, "
                  f"profit factor {r.get('profit_factor','?')}")
    except (json.JSONDecodeError, OSError):
        pass


def _section_verdict(trades_info, n_decisions):
    print("\n[7] VERDICT  (plain language)")
    if not trades_info or trades_info.get("n", 0) < 20:
        print("    Not enough closed trades yet to judge (need ~50).")
        print("    Keep it running on demo and check again in a few days.")
    else:
        pf = trades_info.get("pf")
        if pf is not None and pf >= 1.15:
            print("    Profit factor above 1.15 — promising! Keep collecting data")
            print("    before trusting it with real money.")
        elif pf is not None and pf >= 1.0:
            print("    Profit factor around 1.0 — break-even. Watch another week")
            print("    before any changes.")
        else:
            print("    Profit factor below 1.0 — the current settings are losing.")
            print("    Next step: backtest on history and tune (we do this together).")
    if n_decisions and n_decisions < 100:
        print("    Activity is low — the market may be quiet or the signal bar")
        print("    may be too high. Check AI_MIN_SIGNAL_STRENGTH in .env.")


# --------------------------------------------------------------------------- #
# HTML report (pretty, opens in the browser)
# --------------------------------------------------------------------------- #
def _build_html(decisions, outcomes, days, span) -> str:
    """Build a self-contained HTML report (inline CSS, no internet needed)."""
    esc = html.escape

    # -- metrics ------------------------------------------------------------
    n_dec = len(decisions)
    gate = getattr(config, "AI_MIN_SIGNAL_STRENGTH", 10.0)
    asked = sum(1 for r in decisions if _f(r.get("signal_strength")) >= gate)
    strengths = [_f(r.get("signal_strength")) for r in decisions]
    avg_s = sum(strengths) / len(strengths) if strengths else 0.0
    ai_actions = Counter(r.get("ai_action", "?") or "?" for r in decisions)
    ai_conf = [_f(r.get("ai_confidence")) for r in decisions
               if _f(r.get("ai_confidence")) > 0]
    avg_ai = sum(ai_conf) / len(ai_conf) if ai_conf else 0.0

    pnls = [_f(r.get("pnl")) for r in outcomes]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    total_pnl = sum(pnls)
    wr = 100.0 * len(wins) / len(outcomes) if outcomes else None
    pf = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else None

    # -- day-by-day table ----------------------------------------------------
    dec_by_day = defaultdict(list)
    for r in decisions:
        ts = (r.get("timestamp") or "").strip()
        if ts:
            dec_by_day[ts[:10]].append(r)
    out_by_day = defaultdict(list)
    for r in outcomes:
        ts = (r.get("timestamp") or "").strip()
        if ts:
            out_by_day[ts[:10]].append(r)
    all_days = sorted(set(dec_by_day) | set(out_by_day))
    rows_html = ""
    for d in all_days:
        decs = dec_by_day.get(d, [])
        outs = out_by_day.get(d, [])
        ss = [_f(r.get("signal_strength")) for r in decs]
        avg = sum(ss) / len(ss) if ss else 0.0
        a = sum(1 for r in decs if _f(r.get("signal_strength")) >= gate)
        ai = Counter(r.get("ai_action", "?") or "?" for r in decs)
        dp = [_f(r.get("pnl")) for r in outs]
        dw = sum(1 for p in dp if p > 0)
        dwr = (100.0 * dw / len(dp)) if dp else None
        pnl_s = f"{sum(dp):+.2f}" if dp else "—"
        pnl_cls = "pos" if dp and sum(dp) > 0 else ("neg" if dp else "mut")
        wr_s = f"{dwr:.0f}%" if dwr is not None else "—"
        rows_html += (
            f"<tr><td>{esc(d)}</td><td>{len(decs)}</td>"
            f"<td>{avg:.1f}</td><td>{a}</td>"
            f"<td>{ai.get('BUY',0)}/{ai.get('SELL',0)}/{ai.get('HOLD',0)}</td>"
            f"<td>{len(outs)}</td><td class='{pnl_cls}'>{pnl_s}</td>"
            f"<td>{wr_s}</td></tr>"
        )

    # -- health --------------------------------------------------------------
    log_files = [f for f in LOGS.glob("trading_*.log") if f.is_file()]
    err = warn = 0
    cutoff = datetime.now() - timedelta(days=max(days, 7))
    for f in log_files:
        try:
            if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
                continue
            for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
                if " ERROR " in line or " ERROR[" in line:
                    err += 1
                elif " WARNING " in line:
                    warn += 1
        except OSError:
            continue

    # -- verdict --------------------------------------------------------------
    verdict, vcolor = "Keep it running — not enough trades yet to judge.", "#8a6d00"
    if outcomes and len(outcomes) >= 20 and pf is not None:
        if pf >= 1.15:
            verdict = ("Profit factor above 1.15 — promising! Keep collecting "
                       "data before trusting it with real money.")
            vcolor = "#1a7a1a"
        elif pf >= 1.0:
            verdict = "Break-even (profit factor ~1.0). Watch another week."
            vcolor = "#8a6d00"
        else:
            verdict = ("Profit factor below 1.0 — losing. Backtest and tune "
                       "the settings.")
            vcolor = "#a00"

    def card(label, value, sub=""):
        return (f"<div class='card'><div class='clabel'>{esc(label)}</div>"
                f"<div class='cvalue'>{value}</div>"
                f"<div class='csub'>{esc(sub)}</div></div>")

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Gold Robot Report — {esc(span)}</title>
<style>
  body {{ font-family: Segoe UI, Arial, sans-serif; margin:0; background:#0f1419;
         color:#e6e6e6; }}
  .wrap {{ max-width: 900px; margin: 0 auto; padding: 24px; }}
  h1 {{ font-size: 22px; margin: 0 0 4px; color:#f5c518; }}
  .sub {{ color:#9aa4ad; font-size: 13px; margin-bottom: 18px; }}
  .cards {{ display:flex; flex-wrap: wrap; gap: 10px; margin-bottom: 20px; }}
  .card {{ background:#1a2028; border:1px solid #2a333d; border-radius:10px;
          padding: 12px 16px; min-width: 130px; flex:1; }}
  .clabel {{ font-size: 11px; color:#9aa4ad; text-transform: uppercase;
            letter-spacing: .5px; }}
  .cvalue {{ font-size: 24px; font-weight: 600; margin: 4px 0; }}
  .csub {{ font-size: 11px; color:#7a848d; }}
  h2 {{ font-size: 15px; color:#f5c518; margin: 22px 0 8px;
       border-bottom: 1px solid #2a333d; padding-bottom: 6px; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
  th, td {{ padding: 7px 9px; text-align: right; border-bottom: 1px solid #222a32; }}
  th {{ color:#9aa4ad; font-weight: 600; }}
  td:first-child, th:first-child {{ text-align: left; }}
  .pos {{ color: #4cc38a; }} .neg {{ color: #ff6b6b; }} .mut {{ color: #9aa4ad; }}
  .verdict {{ background:#1a2028; border-left: 4px solid #f5c518; padding: 14px 16px;
             border-radius: 8px; margin-top: 20px; }}
  .verdict b {{ color: #f5c518; }}
  .foot {{ color:#7a848d; font-size: 11px; margin-top: 24px; }}
</style></head><body><div class="wrap">
<h1>🥇 Gold Robot — Report</h1>
<div class="sub">Period: {esc(span)} &nbsp;•&nbsp; Generated {datetime.now():%Y-%m-%d %H:%M}</div>

<div class="cards">
  {card("Decisions", n_dec, "analysis cycles logged")}
  {card("AI asked", asked, f"when strength ≥ {gate:.0f}")}
  {card("Closed trades", len(outcomes), "completed trades")}
  {card("Win rate", (f"{wr:.1f}%" if wr is not None else "—"), "winning trades")}
  {card("Total PnL", f"{total_pnl:+.2f}", "points")}
  {card("Profit factor", (f"{pf:.2f}" if pf is not None else "—"), ">1.0 = winning")}
</div>

<h2>📅 Day by day</h2>
<table>
<tr><th>Date</th><th>Decisions</th><th>Avg signal</th><th>AI asked</th>
<th>AI B/S/H</th><th>Trades</th><th>PnL</th><th>Win%</th></tr>
{rows_html}
</table>

<h2>🧠 What the robot thought</h2>
<div class="cards">
  {card("Avg signal strength", f"{avg_s:.1f}", "out of 100")}
  {card("Avg AI confidence", f"{avg_ai:.1f}%", "when AI answered")}
  {card("AI: BUY / SELL / HOLD",
        f"{ai_actions.get('BUY',0)} / {ai_actions.get('SELL',0)} / {ai_actions.get('HOLD',0)}",
        "Gemini answers")}
  {card("Errors (7d)", err, "log errors")}
  {card("Warnings (7d)", warn, "log warnings")}
</div>

<div class="verdict"><b>Verdict:</b> <span style="color:{vcolor}">{verdict}</span></div>
<div class="foot">Generated by robot_report.py — this file is saved at
data/robot_report.html and is refreshed every time you run the report.</div>
</div></body></html>"""


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Full health + performance report of the gold robot.")
    parser.add_argument("--days", type=int, default=0,
                        help="only look at the last N days (0 = everything)")
    parser.add_argument("--html", action="store_true",
                        help="also save a pretty HTML report "
                             "(data/robot_report.html)")
    args = parser.parse_args()

    decisions = _recent(_read_csv(DATA / "decisions_log.csv"), args.days)
    outcomes = _dedupe_outcomes(
        _recent(_read_csv(DATA / "trade_outcomes.csv"), args.days))

    span = (f"last {args.days} days" if args.days > 0 else "all time")
    print(BAR)
    print(f"  GOLD ROBOT — FULL REPORT   ({span})")
    print(f"  Generated: {datetime.now():%Y-%m-%d %H:%M}")
    print(BAR)

    _section_activity(decisions, args.days)
    _section_daily(decisions, outcomes)
    _section_thought(decisions, args.days)
    trades_info = _section_trades(outcomes, args.days)
    _section_health(args.days)
    _section_history(args.days)
    _section_verdict(trades_info, len(decisions))

    print("\n" + BAR)
    print("  Tip: python robot_report.py --days 7   (last week)")
    print("       python robot_report.py --days 30  (last month)")
    print(BAR)

    # save the pretty HTML report (so it can be opened in the browser)
    if args.html:
        try:
            out = DATA / "robot_report.html"
            out.write_text(_build_html(decisions, outcomes, args.days, span),
                           encoding="utf-8")
            print(f"\n  HTML report saved -> {out}")
        except OSError as exc:
            print(f"  (could not save HTML report: {exc})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
