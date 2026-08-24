# TOMORROW — your easy step-by-step plan

Read one box at a time. Do the boxes in order. Each box is one small job.

---

## Box 1 — Change your Rithmic password (5 minutes, security)

Your old password was shown in some error messages. Change it now:

1. Open **R|Trader Pro** → log in → "Click here to change your password".
2. Set a new password.
3. Open `.env` → update this line:
   ```
   RITHMIC_PASSWORD=your_new_password
   ```
4. Save.

---

## Box 2 — Get free Databento data (10 minutes)

Rithmic's API costs ~$100/month. Databento gives you **$125 free credits**
and works with your robot already.

1. Go to **https://databento.com** → sign up (free, 5 minutes).
2. Copy your **API key**.
3. Open `.env` and set these lines:
   ```
   DATA_SOURCE=databento
   DATABENTO_API_KEY=your_key_here
   ```
4. Save.

---

## Box 3 — Install Databento's tool (2 minutes)

In your black window (with `(venv)` showing):

```
pip install databento
```

---

## Box 4 — Run the robot and see REAL gold data (the fun part)

```
python main.py
```

Check the first line of the summary table. You want to see:

```
STEP 1  DATA ACQUISITION     OK (databento, data=GC.n.0 -> trade=XAUUSD, has_data=True)
```

- ✅ `has_data=True` = real market data is flowing into your robot.
- ✅ The LEVEL 2 and LEVEL 3 sections will show real numbers.

> If the market is CLOSED (weekend / outside US hours), the robot will say
> `SAFETY: SESSION CLOSED` — that is correct, it waits for the market.
> Try again during US trading hours.

---

## Box 5 — Install MetaTrader 5 (30 minutes)

1. Download MT5 from your broker or metatrader5.com.
2. Install it on your Windows computer.
3. Open it → log in with a **DEMO account** (fake money — free).
4. In MT5, open the **Market Watch** → find **XAUUSD** → open its chart.

---

## Box 6 — Watch the signals first (no trading yet)

1. In MT5 press `F4` (opens MetaEditor).
2. File → Open Data Folder → MQL5 → Indicators.
3. Copy `GoldSignalIndicator.mq5` (from `mt5_ea`) into that folder.
4. In MetaEditor press `F7` (Compile). It should say **0 errors**.
5. Back in MT5, drag "GoldSignalIndicator" onto the XAUUSD chart.
6. In `.env`, set the path where MT5 reads files:
   ```
   MT5_SIGNAL_FILE=C:\Users\Jafar\AppData\Roaming\MetaQuotes\Terminal\Common\Files\gold_signal.txt
   ```
   (find your exact path in MT5: File → Open Data Folder, then look at the
   `Common` → `Files` folder — copy that full path.)
7. Run `python main.py` → green arrow = BUY, red arrow = SELL.

This step only WATCHES. Nothing trades. Safe.

---

## Box 7 — Let it trade automatically (DEMO money only)

1. In MetaEditor: File → Open Data Folder → MQL5 → Experts.
2. Copy `GoldTradingEA.mq5` (from `mt5_ea`) into that folder.
3. Press `F7` (Compile). Should say **0 errors**.
4. In MT5, drag "GoldTradingEA" onto the XAUUSD chart.
5. A settings window opens:
   - `InpManualLots` = your position size (start with `0.01`)
   - `InpMinConfidence` = leave `70`
   - `InpUseSignalSLTP` = leave `true`
6. Click OK.
7. Turn ON **AutoTrading** (the button at the top of MT5).

Now the robot opens/closes/reverses trades on DEMO money, fully automatic.
You only ever change the position size (`InpManualLots`).

---

## Box 8 — The coming weeks (be patient)

1. Run `python main.py --loop` to keep it running.
   (Turn off: press Ctrl+C in the black window.)
2. Watch it trade on demo for 2–4 weeks.
3. Run `python backtest.py` to check the strategy.
4. Only think about real money AFTER all this + a winning backtest.

---

## If something goes wrong — check these

| Problem | Fix |
|---|---|
| `has_data=False` | Databento key wrong, or market closed. Check `.env`. |
| `SAFETY: SESSION CLOSED` | Weekend / market closed. Normal — wait. |
| MT5 "cannot compile" | Check the `.mq5` file is copied correctly. |
| No arrows on chart | Check `MT5_SIGNAL_FILE` path. |
| No trades open | Confidence < 70%, or news time, or weekend — the bot is protecting you. |

Still stuck? Run `python demo_step2.py` and `python main.py`, then paste me
what you see.
