# How to run the bot WITHOUT typing commands every time

The Python program must run in the background to feed MT5. Here are the easy
ways to never start it manually again.

---

## Option 1 (easiest) — double-click a file

Two ready-made files are in this folder:

| File | What it does |
|---|---|
| `start_bot.bat` | **double-click** → starts the bot and keeps it running |
| `start_test.bat` | double-click → runs the MT5 connection test once |

To stop the bot: close its black window (or press Ctrl+C inside it).

That's it — no more typing `python ...` every time.

---

## Option 2 (fully automatic) — start with Windows

Make the bot start automatically when you turn on the computer:

1. Press `Win + R`, type `shell:startup`, press Enter
   (this opens the "Startup" folder).
2. Right-click inside it → New → Shortcut.
3. In "location", browse to `start_bot.bat` in this folder and select it.
4. Name it "Gold Trading Bot" → Finish.

Now every time Windows starts, the bot starts too. To stop it later, just
close the black window.

> Note: MT5 must ALSO auto-start (right-click the MT5 shortcut → copy it into
> the same Startup folder), and MT5 must be logged in with AutoTrading on.

---

## Option 3 (most reliable for live trading) — a VPS

When you later want the bot to run 24/7 without your computer being on, rent
a cheap Windows VPS (a few dollars a month), copy the folder there, and do
Options 1 + 2 on the VPS. The bot and MT5 run in the cloud day and night.

---

## Why Python still has to run (honest answer)

MT5's own language (MQL5) cannot run the bot's "brain":
- the 25+ signals (numpy/pandas math),
- order-flow analysis (CVD, OFI, footprint, order blocks),
- the Gemini AI decision.

So the arrangement is:

    Python (the brain, runs in background)
        |  writes gold_signal.txt
        v
    MT5 indicator (draws arrows)  +  MT5 EA (opens/closes/reverses trades)

The indicator and EA ARE inside MT5 — only the brain stays in Python, and
Options 1 + 2 make that brain start itself automatically.

---

## Quick recap of the 3 files you now have

- `start_bot.bat`      → one-click start
- `start_test.bat`     → one-click connection test
- `AUTOSTART_GUIDE.md` → this guide

Suggested workflow after install:
1. Double-click `start_test.bat` (with MT5 open) → confirm data flows.
2. Double-click `start_bot.bat` → let it run.
3. (Optional) add `start_bot.bat` to Windows Startup (Option 2).
