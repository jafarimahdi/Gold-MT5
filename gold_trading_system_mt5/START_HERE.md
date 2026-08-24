# START HERE — How to use the Gold Trading Bot

This guide is written in simple English. Follow the steps one by one.
Do not skip steps. Take your time.

---

## Your 3 questions — answered first (quick answers)

### Q1. Is the robot fully automatic? Can I still change the position size?

**Yes — fully automatic.** The robot now does everything by itself:
- OPENS a position (BUY or SELL) when the signal is strong enough
- CLOSES it when the opposite signal arrives
- REVERSES automatically (closes the old position and opens the new one)

The only thing YOU control is the **position size**. You set it in MT5:

1. Attach the EA to the chart (see Part 6).
2. In the EA settings window there is a field: `InpManualLots`.
3. Type your size there (for example `0.01`, `0.02`, or `0.10`).
4. Click OK.

To change the size at any time: right-click the chart → Expert Advisors →
Properties → change `InpManualLots` → OK. It takes effect on the next trade.

Example: you want to change from 0.01 to 0.02 → just change that number.
That is the only thing you need to touch. Everything else is automatic.

### Q2. Does my computer have to always run this program? How do I turn it on/off?

**Yes — while you want live trading, the program must be running.** It is the
"pump" that reads market data and writes the signal file that MT5 reads.
If you close it, MT5 keeps running but receives no new signals.

- **Turn ON (run forever):**  `python3 main.py --loop`
- **Turn OFF:** press `Ctrl` + `C` in the black window, or just close it.

There is also a **master switch** in `.env`:

```
TRADING_ENABLED=1    <- ON (normal)
TRADING_ENABLED=0    <- OFF (analyse only, never trade)
```

If you set it to `0`, the program still runs and analyses, but it writes
"NEUTRAL" to MT5 — so the robot watches but never opens a position. This is
the safe way to "acknowledge" the bot is off without closing anything.
The log will show: `SAFETY: SWITCH -> TRADING OFF`.

### Q3. Where do I put the Gemini AI key (the "brain")?

In the `.env` file. Find this line and paste your key:

```
GEMINI_API_KEY=paste_your_key_here
```

Get a key (free) at: https://aistudio.google.com/app/apikey

That's it — nothing else to change. The program reads it automatically in
Step 3. **Without a key, the AI always says HOLD, so the robot never opens a
position.** That is why adding the key matters.

How it works together:
- Step 2 looks at the market and builds a picture (trend, order flow, etc).
- Step 3 (Gemini = the brain) looks at that picture and decides BUY / SELL / HOLD
  with a confidence %.
- Step 4 opens the position **only if** the AI is confident (70%+) AND all
  your safety rules are OK (market open, data flowing, not in news blackout,
  no big loss today).

Your earlier conditions (confidence threshold, news windows, risk limits)
all still work exactly as before — the AI decides, the safety gates protect.

---

## What is this program?

This program looks at the gold market. It reads data about who is buying
and who is selling. Then it decides: BUY, SELL, or do nothing.

It can also trade for you on MetaTrader 5 (MT5). But do NOT let it trade
with real money until the end of this guide.

**Important:** Use DEMO accounts first. Demo = fake money. It is safe.

---

## What do you need? (checklist)

| Thing | What it is | Cost |
|-------|-----------|------|
| A computer | Windows works best (MT5 needs Windows) | you have one |
| Python 3 | the program language | free |
| MetaTrader 5 | the trading platform | free |
| Rithmic demo account | gives you real market data | free demo |
| MT5 demo account | fake money to test trading | free |
| Gemini API key | the AI brain | free |

---

# PART 1 — First time setup (do this ONE time)

## Step 1 — Open the program folder

The folder is called `gold_trading_system`.

Inside you see files like:
- `main.py`  (this runs everything)
- `config.py`
- `step2_market_analysis.py`  (the brain)
- and more

## Step 2 — Install Python

1. Go to python.org
2. Download Python 3 (version 3.9 or newer)
3. Install it. **Tick the box that says "Add Python to PATH".**

To check it works, open the black window (Command Prompt) and type:

```
python --version
```

You should see something like `Python 3.12`.

## Step 3 — Install the extra packages

The best way on Windows is a **virtual environment** — a private copy of the
tools that lives inside your folder. It never touches the protected
`C:\Python312` folder, so it never asks for admin rights.

Open the black window (Git Bash). Go into the program folder:

```
cd ~/Documents/gold_trading_system
```

Then type these four lines, one after another:

```
python -m venv venv
source venv/Scripts/activate
pip install -r requirements.txt
python demo_step2.py
```

- After `source venv/Scripts/activate` the prompt will show `(venv)`.
  That means you are inside the private environment.
- After `pip install -r requirements.txt` wait until it finishes
  (a few minutes, lots of text).
- After `python demo_step2.py` you should see `36/36 passed`.

**From now on, every time you open a NEW terminal to use the bot, first type:**

```
cd ~/Documents/gold_trading_system
source venv/Scripts/activate
```

Then run your commands (`python main.py`, etc).

If you prefer to skip the virtual environment, you can instead open the
terminal **as Administrator** (right-click → "Run as administrator") and run
`python -m pip install -r requirements.txt`.

## Step 4 — Make your settings file

In the folder there are two files:

- `.env.example` — this is a **template** (a reference sheet). Never rename it.
- `.env` — this is your **real settings file**.

**If `.env` already exists** (it does if you used `setup_markets.py`):
keep it and just add the missing lines to it (see Step 10).

**If `.env` does NOT exist yet:**

1. Copy `.env.example`.
2. Rename the copy to `.env`  (just `.env`, nothing else).

Either way, `.env.example` stays where it is. You will edit `.env` later
to add your passwords and the Gemini key.

---

# PART 2 — Check the program works (no accounts needed)

## Step 5 — Run the test

In the black window, inside the folder, type:

```
python3 demo_step2.py
```

(On Windows, if `python3` does not work, type `python` instead.)

You should see at the end:

```
-> 36/36 passed
Done. Exiting successfully.
```

If you see this: **the brain works.** ✅

## Step 6 — Run the whole program (demo mode)

Type:

```
python3 main.py
```

You should see a big report. It shows:
- the market picture (price, trend, order flow)
- at the end, a summary table with STEP 1 to STEP 5

It will look like:

```
STEP 1  DATA ACQUISITION     OK (demo ...)
STEP 2  MARKET ANALYSIS      OK -> BUY (...)
STEP 3  AI DECISION          HOLD @ 0.0%
STEP 4  EXECUTION            SKIPPED ...
STEP 5  MONITORING           OK
```

This is the program running with **fake demo data**. It works but is not
connected to the real market yet.

---

# PART 3 — Choose your markets

The program reads data from ONE market and trades on ANOTHER market.

- **DATA market** = where the real order data comes from (Rithmic).
  For gold this is usually `GC` (futures).
- **TRADE market** = the market you trade on MT5.
  For gold this is usually `XAUUSD`.

## Step 7 — Pick the markets

Type:

```
python3 setup_markets.py
```

The program will ask you two questions. Answer them:

1. DATA (futures feed) symbol: type `GC`
2. TRADE (MT5 CFD) symbol: type `XAUUSD`

Then it asks "Is everything correct?" — type `y` and press Enter.

## Step 8 — Check it saved correctly

Type:

```
python3 setup_markets.py --check
```

You should see at the end: `RESULT: mapping OK`.

---

# PART 4 — Connect real data (Rithmic demo)

## Step 9 — Get a free Rithmic demo account

1. Go to the Rithmic website.
2. Sign up for a demo account (paper trading).
3. They give you a **username** and **password**.
4. Rithmic demo passwords CHANGE sometimes. When they change, you just
   edit `.env` again. Easy.

## Step 10 — Put your username and password in `.env`

Open the `.env` file with Notepad.

If your `.env` is empty or very short (only has the market lines), add these
lines to it. If the lines already exist, just fill them in:

```
DATA_SOURCE=rithmic
RITHMIC_USERNAME=your_username_here
RITHMIC_PASSWORD=your_password_here
```

Save the file.

## Step 10b — Add the Gemini AI key (the brain)

The Gemini AI is the **brain** of the robot. It looks at the market picture
and decides BUY, SELL, or HOLD.

1. Get a free key at: https://aistudio.google.com/app/apikey
2. Open the `.env` file again with Notepad.
3. Find this line (if it is not there, add it):

```
GEMINI_API_KEY=
```

4. Paste your key after the `=` sign:

```
GEMINI_API_KEY=AIzaSyYourKeyHere1234567890
```

5. Save the file.

That is all. The program reads this key automatically.

**Why this matters:** without a key, Step 3 always says "HOLD", so the robot
never opens a position. With the key, the brain makes real decisions.

How it works:
- Step 2 looks at the market and builds a picture (trend, order flow, CVD...).
- Step 3 (Gemini = the brain) looks at that picture and says BUY / SELL / HOLD
  with a confidence %.
- Step 4 opens the position only if the brain is confident (70%+) AND all
  your safety rules are OK.

## Step 11 — Install the Rithmic bridge (the connector)

Rithmic's official API has no Python support, so the program uses a free
connector package called **async-rithmic**.

In the black window (with `(venv)` active), type:

```
pip install async-rithmic
```

Wait for it to finish.

## Step 12 — Test your Rithmic connection FIRST

Before running the whole bot, test that your Rithmic login works:

```
python rithmic_test.py
```

You should see it connect, find the gold contract (GC on COMEX), and then
print lines like `TICK: {...}` and `BOOK: {...}` for about 15 seconds.

- If you see those lines → **your Rithmic login works.** Continue to Step 13.
- If you see `No data arrived` → the market may be closed (weekend), or COMEX
  market data is not enabled on your demo account.
- If you see an error → copy the whole message and send it to me.

> **Note:** you must also log into R|Trader Pro once and accept the
> market-data agreement, and your demo account must have COMEX/CME market
> data enabled. Rithmic support can enable it for you.

## Step 13 — Run with real data

Type:

```
python main.py
```

Now look at the report. Check these things:

1. It says `has_data=True` (this means real data is coming).
2. In the "LEVEL 2" section you see numbers (this is the real order book).
3. In the "LEVEL 3" section you see numbers (real order events).

If it says `has_data=False` or `SAFETY: FEED STALE` — the data is not coming.
Run `python rithmic_test.py` again to see what is wrong.

> **Note:** gold data only flows during market hours. On the weekend the
> program will say `SAFETY: SESSION CLOSED — WEEKEND`. This is CORRECT and
> safe — it will not crash and will not trade. It waits for Monday.

---

# PART 5 — Watch the signals on MT5 (no trading yet)

## Step 14 — Install MetaTrader 5

1. Download MT5 from your broker's website (or metatrader5.com).
2. Install it on your Windows computer.
3. Open MT5 and log into a **demo account** (fake money).

## Step 15 — Put the indicator in MT5

The folder `mt5_ea` has two files:

- `GoldSignalIndicator.mq5` — draws arrows on the chart (watch only)
- `GoldTradingEA.mq5` — trades for you (later!)

1. In MT5, press `F4` or open MetaEditor.
2. In MetaEditor: File → Open Data Folder → MQL5 → Indicators.
3. Copy `GoldSignalIndicator.mq5` into the Indicators folder.
4. In MetaEditor press `F7` (Compile). It should say "0 errors".
5. Go back to MT5. Open a gold chart (XAUUSD).
6. Drag the "GoldSignalIndicator" onto the chart.

Now when the program runs, you will SEE arrows on the chart:
- green arrow = BUY
- red arrow = SELL

This is only watching. No trading happens yet. Safe.

## Step 16 — Tell the program where to write the signal

The program writes a small file that MT5 reads. You must tell it where.

In MT5: File → Open Data Folder → find the `Common` → `Files` folder.
Copy that full path.

Open `.env` and find:

```
MT5_SIGNAL_FILE=
```

Write the path (example):

```
MT5_SIGNAL_FILE=C:\Users\YourName\AppData\Roaming\MetaQuotes\Terminal\Common\Files\gold_signal.txt
```

Save the file.

Run `python3 main.py` again. The file `gold_signal.txt` should appear in
that folder.

---

# PART 6 — Let it trade automatically (DEMO money only!)

## Step 17 — Install the EA (the trader)

1. In MetaEditor: File → Open Data Folder → MQL5 → Experts.
2. Copy `GoldTradingEA.mq5` into the Experts folder.
3. Press `F7` (Compile). Should say "0 errors".
4. In MT5, drag the "GoldTradingEA" onto the XAUUSD chart.
5. A settings window opens. Set your values:
   - `InpManualLots` = **your position size** (e.g. 0.01 or 0.02). This is YOUR choice.
   - `InpMinConfidence` = 70 (leave as is).
   - `InpUseSignalSLTP` = `true` to let the bot set its own stop-loss and
     take-profit, or `false` to manage them yourself.
6. Click "OK".
7. Turn ON "AutoTrading" (the button at the top of MT5).

Now the bot is fully automatic on a DEMO account (fake money):
- it OPENS positions,
- it CLOSES them when the signal reverses,
- it REVERSES automatically (close old + open new).

**The only thing you control is the position size (`InpManualLots`).**
To change it (e.g. 0.01 → 0.02): right-click the chart → Expert Advisors →
Properties → change `InpManualLots` → OK. Takes effect on the next trade.

The bot has safety rules. It will NOT open a position:
- on weekends
- when data is missing
- during big news events
- when the AI confidence is below 70%
- after a big daily loss
- when you set TRADING_ENABLED=0

## Step 18 — Watch it for 2 to 4 weeks

Let it run on demo. Watch:

- Are the arrows correct?
- Do trades open only when they should?
- Do trades stay closed during news?

This is the most important step. Be patient.

---

# PART 7 — Test your strategy with the backtest

## Step 19 — Backtest (see if the strategy would have won)

The backtest replays history to see if your signals would have made money.

```
python3 backtest.py
```

It shows:
- number of trades
- win rate (%)
- total return
- profit factor (bigger than 1 = good)
- maximum drawdown (how much it can lose)

**Honest warning:** right now, on fake data, the strategy does NOT make
money. That is normal and expected. The point of the backtest is to tune the
settings with REAL data until it shows a profit.

To record real data so you can backtest it later, set in `.env`:

```
RECORD_DATA=1
```

The program will save the real data into the `data` folder as
`record_...json` files.

Then backtest that real data:

```
python3 backtest.py --replay data/record_2026_08_19_120000.json
```

(Use the real file name you see in the data folder.)

---

# PART 8 — Before real money (final checklist)

Do ALL of these before you use real money:

1. ✅ All tests pass (36/36 in Step 5).
2. ✅ The program runs on weekends without crashing or trading.
3. ✅ Real Rithmic data arrives (`has_data=True`).
4. ✅ The MT5 indicator shows correct arrows.
5. ✅ The EA trades correctly on DEMO for 2–4 weeks.
6. ✅ The backtest with REAL data shows profit (profit factor > 1).
7. ✅ You have watched the daily-loss safety stop working.

Only when ALL of these are done, think about real money.

---

# Quick command list (cheat sheet)

| What you want | Type this |
|---------------|-----------|
| Run the test | `python3 demo_step2.py` |
| Run the whole program once | `python3 main.py` |
| Run it forever (loop) | `python3 main.py --loop` |
| Choose markets | `python3 setup_markets.py` |
| Check markets | `python3 setup_markets.py --check` |
| Backtest | `python3 backtest.py` |
| All tests | see `paper_trade_checklist.md` |

---

# If something goes wrong (common errors and how to fix them)

### Error: `ERROR: Could not open requirements file: ... requirements.txt`
This means your black window is in the wrong folder (not inside
`gold_trading_system`).

**Fix:** type `cd gold_trading_system` first, then try again.
Type `ls` to check you can see `requirements.txt` and `main.py`.

### Error: `pip ... Access is denied` or `PermissionError` (when in Program Files)
You are running the program from a **protected Windows folder** like
`C:\Program Files`. That folder needs admin rights, so the program cannot
write its files.

**Fix:** move the `gold_trading_system` folder to your own user folder:

```
C:\Users\Jafar\Documents\gold_trading_system
```

Then open the black window and go there:

```
cd C:/Users/Jafar/Documents/gold_trading_system
```

### Error: `Failed to write executable ... idna.exe ... .deleteme` / `WinError 5 Access is denied`
pip is trying to write into the protected `C:\Python312` folder and Windows
is blocking it.

**Fix (recommended):** use a virtual environment (see Step 3) — it installs
everything inside your own folder, no admin needed.

**Alternative fix:** open the terminal as Administrator (right-click the Git
Bash icon → "Run as administrator"), then run
`python -m pip install -r requirements.txt`.

### Note: "A new release of pip is available ... upgrade"
**You can ignore this message.** It is only a suggestion. You do NOT need to
upgrade pip to run this program.

### Error: `Python was not found ... Microsoft Store`
This happens when you type `python3` on Windows.
**Fix:** type `python` instead of `python3`. Example: `python main.py`

### Error: `ModuleNotFoundError: No module named 'pandas'`
This means the extra packages are not installed yet.
**Fix:** in the black window, inside the folder, type:

```
python -m pip install -r requirements.txt
```

Wait until it finishes (it can take a few minutes). Then try again.

### Error: `PermissionError: [Errno 13] Permission denied ... logs\trading_....log`
This means the program cannot write its log file. It can happen if:
- you are running the program from a special drive (like `A:`), a cloud
  folder (OneDrive/Google Drive), or a read-only folder,
- the log file is open in another program,
- another copy of the bot is already running.

**Fix (best):** copy the whole `gold_trading_system` folder to a normal place,
like `C:\Users\Jafar\Documents\gold_trading_system`, and run it from there.

The program is now protected against this error: even if it cannot write the
log file, it will keep running and only print to the screen (no crash).
But the data files (decisions, snapshots) also need a writable folder, so
moving to `C:\` is still the right fix.

### Error: `No Rithmic Python transport configured` or `async-rithmic not installed`
This means the Rithmic connector package is missing.

**Fix:** type `pip install async-rithmic` (inside the `(venv)`), then test with
`python rithmic_test.py`.

### Error: `rithmic_test.py` connects but `No data arrived`
Possible causes:
1. The market is closed (weekend / outside CME trading hours).
2. COMEX/CME market data is not enabled on your demo account — ask Rithmic
   support to enable it.
3. You have not logged into R|Trader Pro and accepted the market-data
   agreement yet.
4. Wrong system name — try `RITHMIC_SYSTEM=Rithmic Paper Trading`.

### Other problems

1. **Program says `has_data=False`** → Rithmic not sending data. Check
   username/password, internet, and that the market is open.
2. **Program says `SAFETY: SESSION CLOSED`** → it is weekend. Normal. Wait.
3. **MT5 says "cannot compile"** → check you copied the `.mq5` file correctly
   and MetaEditor is installed.
4. **No arrows on chart** → check `MT5_SIGNAL_FILE` path in `.env`.
5. **Trades not opening** → confidence is below 70%, or news blackout, or
   weekend. This is the bot protecting you. Correct behaviour.

Still stuck? Run `python setup_markets.py --check` and `python demo_step2.py`
again and send me what you see.
