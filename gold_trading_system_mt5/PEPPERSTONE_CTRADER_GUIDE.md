# 🚀 Switching to Pepperstone + cTrader — Step-by-Step Guide

This guide has TWO parts:
- **PART 1**: Move the robot to **Pepperstone MT5** (easy — almost nothing changes)
- **PART 2**: If MT5 gives no Level 2, move to **Pepperstone cTrader** (bigger change)

Do PART 1 first. Only do PART 2 if PART 1 shows "0 book updates".

---

## PART 1 — Pepperstone MT5 (start here)

### Step 1 — Open a free Pepperstone demo
1. Go to: **https://pepperstone.com**
2. Click **"Create a demo account"** (demo = practice money, free, no card)
3. Fill in: your email, a password, country = **Hungary**
4. Verify your email (check your inbox)
5. In your dashboard, create a **DEMO account**:
   - Platform = **MetaTrader 5**
   - Account type = **Razor** (raw spreads — best for a robot)
   - Currency = **USD**
6. Pepperstone will email you: **Login number**, **password**, and **server name**
   (the server usually looks like `Pepperstone-Demo`)

### Step 2 — Log in to MT5 with Pepperstone
1. Open your existing **MetaTrader 5** terminal
2. Menu: **File → Login to Trade Account**
3. Fill in: Login, Password, Server = `Pepperstone-Demo`
4. Wait ~30 seconds — the chart should start moving (bottom-right shows data)

### Step 3 — Find the exact gold symbol name
This is IMPORTANT — every broker names gold a bit differently.

1. In MT5 press **Ctrl+U** (opens the symbol list)
2. Search for **"XAU"**
3. Write down the EXACT name — it may be:
   - `XAUUSD`   (most likely)
   - `XAUUSD.a` / `XAUUSD+` / `XAUUSDm`  (with a letter/symbol at the end)
4. Note it EXACTLY, including any `+`, `.`, `m` at the end.

### Step 4 — Update your .env file
Open `.env` in Notepad and change these 3 lines to the exact name from Step 3:

```
MT5_SYMBOL=XAUUSD        <- put the exact Pepperstone name here
TRADING_SYMBOL=XAUUSD    <- same
DATA_SYMBOL=XAUUSD       <- same
```

(If the name is `XAUUSD.a`, write `XAUUSD.a` in all three.)

### Step 5 — Run the robot and CHECK the magic line
1. Double-click `start_bot.bat`
2. In the terminal, find this line (it appears every minute):

```
MT5 provider: 50 ticks, 0 book updates for XAUUSD (spread ...)
                            ^^^^^^^^^^^^^^^^
```

**Look at "book updates":**

| You see | What it means | Next step |
|---|---|---|
| **"12 book updates"** (any number above 0) | 🎉 Level 2 works! | Done — your LEVEL 2 section now shows real numbers |
| **"0 book updates"** | MT5 demo gives no depth for gold | Go to **PART 2** below |

Also check the snapshot for:
- `L2 bid/ask depth : 1,234 / 5,678` (not `0 / 0`) → L2 works ✅

---

## PART 2 — Pepperstone cTrader (only if MT5 gave "0 book updates")

cTrader is a different platform (not MetaTrader). It shows a beautiful
**Depth of Market (DOM)** = real Level 2 order book. But its robots are
written in a different language (C#), so this is a **project**, not a
copy-paste. Here is the path:

### Step 1 — Install cTrader
1. In your Pepperstone dashboard: **Platforms → cTrader → Download**
2. Install and log in with the **same demo login** (Pepperstone sends separate
   cTrader demo credentials, or lets you use the same account).

### Step 2 — See the Level 2 for yourself
1. Open cTrader, search for **XAUUSD**, open the chart
2. On the right, open the **"Depth of Market"** panel
3. You will see the **order ladder**: green (buy) and red (sell) sizes at each
   price level — this is the Level 2 data you wanted.

### Step 3 — How we connect the robot (2 options)

**Option A — cBot (everything inside cTrader, in C#)**
- We rewrite the robot's rules in C# using cTrader Automate (its built-in
  editor + backtester).
- Pro: runs 24/7 inside cTrader, no Python needed, native backtesting.
- Con: a full rewrite (the 25 indicators must be re-coded in C#).
- Effort: LARGE. We would do it piece by piece.

**Option B — Hybrid (keep the Python brain, add a cTrader bridge)**
- Keep everything we built (Step 2 analysis + Gemini + news + macro) in Python.
- Add ONE new file: a "cTrader bridge" that uses cTrader's **Open API**
  (official REST/WebSocket API) to read the Depth of Market and to send
  orders.
- Pro: the smart part (your Python + AI) stays exactly as it is.
- Con: needs the Open API to be enabled on the account + careful testing.
- Effort: MEDIUM. This is the path I recommend for you.

### Step 4 — The plan when you're ready
We will do this together, step by step:
1. First, get cTrader showing Level 2 (Steps 1–2 above) — just LOOK at it.
2. Then I write the cTrader bridge (Option B) and we test it on the demo.
3. Then we decide whether a full cBot (Option A) is worth it later.

**Do NOT rush this.** Keep the MT5 robot running on demo the whole time —
it works today and keeps collecting data for your weekly report.

---

## Summary — what changes, what stays

| Part | MT5 → Pepperstone | cTrader |
|---|---|---|
| Python brain (analysis + AI + news + macro) | ✅ stays | ✅ stays |
| Data source | MT5 (same code) | new cTrader bridge |
| Level 2 depth | maybe | ✅ yes (DOM) |
| Execution | your EA (same) | cBot or Open API |
| Effort | ~5 minutes | a real project |
