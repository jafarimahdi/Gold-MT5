# ZERO TO RUNNING — the complete guide, step by step

Follow these steps ONE at a time, from the very beginning until the bot is
fully running on MT5. Do not skip steps. If anything looks different from what
is written here, stop and show me what you see.

---

## PART 1 — Get the application onto your computer

### Step 1 — Download the folder
- In the chat, download the project folder (the zip file
  `gold_trading_system_mt5.zip`).
- Save it to **Downloads**.

### Step 2 — Unzip it to a good place
- Right-click the zip → **Extract All...**
- Extract to:  `C:\Users\Jafar\Documents\gold_trading_system_mt5`
- Do NOT put it in `Program Files` (that folder blocks the bot).

### Step 3 — Check the folder contents
Open the folder. You should see files including:
- `start_bot.bat`  (your one-click start)
- `start_test.bat`
- `main.py`, `mt5_test.py`, `requirements.txt`
- a `data` folder, a `logs` folder, an `mt5_ea` folder

If you see these → the app is correctly downloaded. ✅

---

## PART 2 — Install Python (only if you don't have it)

### Step 4 — Check if Python is installed
- Open the black window (search "Command Prompt" or "Git Bash").
- Type:  `python --version`  and press Enter.
- If it shows something like `Python 3.12` → skip to PART 3.
- If it says "not found" → do Step 5.

### Step 5 — Install Python (only if needed)
1. Go to **python.org**
2. Download **Python 3.12** (Windows installer)
3. Run it. **IMPORTANT: tick the box "Add Python to PATH"** at the bottom.
4. Click Install Now. Wait until it finishes.

---

## PART 3 — Install MetaTrader 5

### Step 6 — Install MT5
1. Download **MetaTrader 5** from your broker's website or metatrader5.com
2. Install it (normal Windows install).

### Step 7 — Log into a DEMO account (fake money — free)
1. Open MT5.
2. File → Open an Account → search for your broker's demo server
   (or "MetaQuotes-Demo").
3. Follow the steps. You'll get a login + password (fake money account).

### Step 8 — Open a gold chart
1. In MT5, press **Ctrl+U** (opens the symbol list).
2. Type `XAUUSD` and add it (double-click).
3. Drag XAUUSD onto the screen to open its chart.

---

## PART 4 — First test of the bot (no trading yet)

### Step 9 — Double-click the test file
- In the project folder, **double-click `start_test.bat`**.
- On the first run it will:
  - create a private environment (one minute), then
  - install packages (a few minutes), then
  - run the MT5 connection test.

### Step 10 — Check the test result
- If it shows **TICK / LEVEL 2 / TICKS / CANDLES** with numbers → your MT5
  data works. ✅
- If it shows an error → copy the message and show me.

---

## PART 5 — Add the AI brain (so it can decide BUY/SELL)

### Step 11 — Get a free Gemini key
1. Go to **aistudio.google.com/app/apikey**
2. Sign in with a Google account.
3. Click **Create API key** and copy it.

### Step 12 — Put the key in `.env`
1. In the project folder, open the file named `.env` with **Notepad**
   (right-click → Open with → Notepad).
2. Find or add the line:
   ```
   GEMINI_API_KEY=paste_your_key_here
   ```
3. Save the file.

> Without this key, Step 3 (the AI) always says HOLD, so the bot never
> opens a position. This step turns the brain ON.

---

## PART 6 — See the signals on the MT5 chart (watch only)

### Step 13 — Install the indicator into MT5
1. In MT5, press **F4** (opens MetaEditor).
2. In MetaEditor: File → Open Data Folder.
3. Go into `MQL5` → `Indicators`.
4. Copy the file `GoldSignalIndicator.mq5` (from the project's `mt5_ea`
   folder) into that Indicators folder.
5. In MetaEditor, find the file on the left, double-click it, then press
   **F7** (Compile). It should say **0 errors**.
6. Close MetaEditor. In MT5, open the Navigator (Ctrl+N) → Indicators →
   drag **GoldSignalIndicator** onto the XAUUSD chart.

### Step 14 — Tell the bot where to write the signal
1. In MT5: File → Open Data Folder → find the `Common` → `Files` folder.
   Copy its full path.
2. In the project folder, open `.env` with Notepad and set:
   ```
   MT5_SIGNAL_FILE=C:\Users\Jafar\AppData\Roaming\MetaQuotes\Terminal\Common\Files\gold_signal.txt
   ```
   (use YOUR exact path from step 1)
3. Save.

### Step 15 — Start the bot and watch
- Double-click **`start_bot.bat`**.
- It keeps running. On the MT5 chart you will now see:
  - 🟢 green arrow = BUY signal
  - 🔴 red arrow = SELL signal
- This step only WATCHES — no trading. Safe.

---

## PART 7 — Let it trade automatically (DEMO money)

### Step 16 — Install the EA into MT5
1. In MT5, press **F4** (MetaEditor).
2. File → Open Data Folder → `MQL5` → `Experts`.
3. Copy `GoldTradingEA.mq5` (from the project's `mt5_ea` folder) into the
   Experts folder.
4. In MetaEditor, double-click it and press **F7** (Compile). Should say
   **0 errors**.

### Step 17 — Attach the EA and set your size
1. In MT5, drag **GoldTradingEA** onto the XAUUSD chart.
2. A settings window opens. Set:
   - `InpManualLots` = **your position size** (start with `0.01`)
   - `InpMinConfidence` = `70` (leave it)
   - `InpUseSignalSLTP` = `true` (let the bot set stop/target)
   - `InpUseTrailing` = `true` (locks in profit)
3. Click OK.

### Step 18 — Turn ON AutoTrading
- At the top of MT5, click the **AutoTrading** button so it turns green.

### Step 19 — Done — it trades fully automatically
The bot now:
- opens positions when the signal + AI agree (confidence ≥ 70%)
- closes and reverses when the opposite signal arrives
- manages stop-loss, take-profit and trailing stop
- protects you: no trading on weekends, during news, when spread is wide,
  after a daily loss, or more than 20 trades/day

---

## PART 8 — Day-to-day use

| What | How |
|---|---|
| Start the bot | double-click `start_bot.bat` |
| Test the connection | double-click `start_test.bat` |
| Stop the bot | close its black window |
| Change position size | right-click chart → Expert Advisors → Properties → `InpManualLots` |
| Turn trading off (watch only) | in `.env` set `TRADING_ENABLED=0` |

---

## If something goes wrong — quick fixes

| Problem | Fix |
|---|---|
| `Python was not found` | install Python and tick "Add to PATH" |
| `No module named pandas` | double-click `start_bot.bat` again (it installs packages) |
| Test shows no data | market closed (weekend), or MT5 not open / not logged in |
| `SAFETY: SESSION CLOSED` | weekend — normal, waits for Monday |
| No arrows on chart | check `MT5_SIGNAL_FILE` path in `.env` |
| No trades open | confidence < 70%, or news blackout, or weekend — the bot is protecting you |
| Permission denied / Access denied | the folder is in Program Files — move it to Documents |

Still stuck? Show me the exact message and I'll help.
