//+------------------------------------------------------------------+
//|                                              GoldTradingEA.mq5    |
//|   Gold Trading System - MT5 Expert Advisor (FULLY AUTOMATED)      |
//|                                                                   |
//|   What it does:                                                   |
//|     - reads the signal file written by the Python pipeline        |
//|       (gold_signal.txt in Common Files)                           |
//|     - OPENS a position (BUY or SELL) when a new signal arrives    |
//|       and confidence is high enough                               |
//|     - if already in the market in the SAME direction -> wait      |
//|     - if already in the OPPOSITE direction -> CLOSE it and        |
//|       OPEN the new position (auto-reverse)                        |
//|                                                                   |
//|   YOU control the position size (InpManualLots).                  |
//|   Everything else is automatic: open, close, reverse.             |
//|                                                                   |
//|   Settings:                                                       |
//|     InpManualLots    -> position size (e.g. 0.01, 0.02, 0.10)     |
//|     InpMinConfidence -> how sure the AI must be (default 70%)     |
//|     InpUseSignalSLTP -> true = use bot SL/TP, false = manage      |
//|                         stop-loss yourself                        |
//|                                                                   |
//|   To change the lot size at any time:                             |
//|   right-click chart -> Expert Advisors -> Properties ->           |
//|   change InpManualLots -> OK. (Takes effect on the next order.)   |
//|                                                                   |
//|   HOW TO INSTALL                                                   |
//|   1) Compile in MetaEditor (F7).                                  |
//|   2) Attach to an XAUUSD chart, enable AutoTrading.               |
//+------------------------------------------------------------------+
#property copyright "Gold Trading System"
#property version   "3.21"
#property strict

#include <Trade\Trade.mqh>

input string InpSignalFile    = "gold_signal.txt"; // Signal file (Common Files)
input double InpManualLots    = 0.01;              // <-- YOUR POSITION SIZE
input double InpMinConfidence = 70.0;              // Min AI confidence (%)
input bool   InpUseSignalSLTP = true;              // Use SL/TP from signal
input double InpFallbackSL    = 30.0;              // Fallback SL (points)
input double InpFallbackTP    = 90.0;              // Fallback TP (points)
input int    InpMagic         = 234000;            // EA magic number
input bool   InpUseTrailing   = true;              // Trail the stop to lock profit
input double InpTrailingPoints = 150.0;            // Trail distance (points)

CTrade trade;
datetime g_lastSignalId = 0;   // id of the last signal already acted upon

//+------------------------------------------------------------------+
int OnInit()
  {
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetTypeFillingBySymbol(_Symbol);
   Print("GoldTradingEA v3.21 attached. Reading file: ", InpSignalFile);
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   // throttle to once per second
   static datetime lastCheck = 0;
   if(TimeCurrent() == lastCheck)
      return;
   lastCheck = TimeCurrent();

   ProcessSignalFile();
   ApplyTrailingStop();
  }

//+------------------------------------------------------------------+
//| Return true when a position belongs to this EA.                  |
//| The account can be hedging, so never use PositionSelect(symbol)  |
//| as a substitute for checking every position's magic number.      |
//+------------------------------------------------------------------+
bool IsBotPosition()
  {
   return(PositionGetInteger(POSITION_MAGIC) == InpMagic &&
          PositionGetString(POSITION_SYMBOL) == _Symbol);
  }

//+------------------------------------------------------------------+
//| Close every bot position for this symbol before a reversal.      |
//+------------------------------------------------------------------+
bool CloseBotPositions()
  {
   bool ok = true;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !IsBotPosition())
         continue;
      if(!trade.PositionClose(ticket))
        {
         Print("GoldTradingEA: could not close bot position ticket=", ticket,
               " retcode=", trade.ResultRetcode());
         ok = false;
        }
     }
   return ok;
  }

//+------------------------------------------------------------------+
//| Move the stop-loss to lock in profit as price moves in our favour |
//+------------------------------------------------------------------+
void ApplyTrailingStop()
  {
   if(!InpUseTrailing)
      return;

   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   if(point <= 0)
      return;

   double trailDist = InpTrailingPoints * point;
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);

   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !IsBotPosition())
         continue;

      long   posType   = PositionGetInteger(POSITION_TYPE);
      double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl        = PositionGetDouble(POSITION_SL);
      double tp        = PositionGetDouble(POSITION_TP);

      if(posType == POSITION_TYPE_BUY)
        {
         double newSL = bid - trailDist;
         // only move the stop UP, and only after we are past break-even
         if((sl <= 0 || newSL > sl) && newSL > openPrice)
            trade.PositionModify(ticket, newSL, tp);
        }
      else if(posType == POSITION_TYPE_SELL)
        {
         double newSL = ask + trailDist;
         // only move the stop DOWN, and only after we are past break-even
         if((sl <= 0 || newSL < sl) && newSL < openPrice)
            trade.PositionModify(ticket, newSL, tp);
        }
     }
  }

//+------------------------------------------------------------------+
//| Read the signal file. Reads with FILE_ANSI (single-byte) because  |
//| the bot writes plain ASCII text. FILE_TXT would decode UTF-16 and |
//| garble it.                                                        |
//+------------------------------------------------------------------+
string ReadSignalFile()
  {
   string content = "";
   int h = FileOpen(InpSignalFile, FILE_READ|FILE_ANSI|FILE_COMMON);
   if(h == INVALID_HANDLE)
      h = FileOpen(InpSignalFile, FILE_READ|FILE_ANSI);
   if(h == INVALID_HANDLE)
      return "";

   while(!FileIsEnding(h))
     {
      string line = FileReadString(h);
      StringTrimRight(line);      // strip trailing \r from CRLF
      content += line + "\n";
     }
   FileClose(h);
   return content;
  }

//+------------------------------------------------------------------+
//| Extract a key=value from the file.                                |
//| NOTE: StringTrimLeft/StringTrimRight modify the string IN PLACE   |
//| and return a number, so they must be called as statements.        |
//+------------------------------------------------------------------+
bool GetValue(string content, string key, string &value)
  {
   string lines[];
   int n = StringSplit(content, '\n', lines);
   for(int i = 0; i < n; i++)
     {
      // trim BOTH ends of each line (removes \r from CRLF files)
      StringTrimLeft(lines[i]);
      StringTrimRight(lines[i]);
      string parts[];
      if(StringSplit(lines[i], '=', parts) == 2)
        {
         StringTrimLeft(parts[0]);
         if(parts[0] == key)
           {
            value = parts[1];
            StringTrimLeft(value);
            StringTrimRight(value);
            return true;
           }
        }
     }
   return false;
  }

//+------------------------------------------------------------------+
//| Process the signal                                               |
//+------------------------------------------------------------------+
void ProcessSignalFile()
  {
   string content = ReadSignalFile();
   if(content == "")
      return;

   string s;
   if(!GetValue(content, "id", s))
      return;
   datetime sigId = (datetime)StringToInteger(s);
   if(sigId <= g_lastSignalId)
      return;                          // already acted on this signal

   // Never act on a signal left behind by a stopped/restarted Python process.
   string expiry;
   if(GetValue(content, "expires_unix", expiry))
     {
      long expiresAt = (long)StringToInteger(expiry);
      if(expiresAt > 0 && (long)TimeCurrent() > expiresAt)
        {
         g_lastSignalId = sigId;
         Print("GoldTradingEA: expired signal ignored (id=", sigId, ")");
         return;
        }
     }
   g_lastSignalId = sigId;

   if(!GetValue(content, "direction", s))
      return;
   string dir = s;

   double conf = 0.0;
   if(GetValue(content, "confidence", s))
      conf = StringToDouble(s);

   string newsState = "";
   GetValue(content, "news_state", newsState);

   // ---- gates --------------------------------------------------------
   if(conf < InpMinConfidence)
      return;
   if(dir != "BUY" && dir != "SELL")
      return;
   if(newsState == "BLACKOUT")
      return;                          // never trade into news

   // ---- current position state ---------------------------------------
   // In a hedging account there can be several positions for one symbol.
   // Never touch a manual or other-EA position, and do not add to it.
   bool hasOtherPosition = false;
   bool hasBotPosition = false;
   long botType = -1;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      if(IsBotPosition())
        {
         if(!hasBotPosition)
            botType = PositionGetInteger(POSITION_TYPE);
         hasBotPosition = true;
        }
      else
         hasOtherPosition = true;
     }

   if(hasOtherPosition)
     {
      Print("GoldTradingEA: another position already exists on ", _Symbol,
            "; no order sent to protect manual/other-EA trades.");
      return;
     }

   int wantType = (dir == "BUY") ? POSITION_TYPE_BUY : POSITION_TYPE_SELL;
   if(hasBotPosition && botType == wantType)
      return;                          // already positioned correctly

   // ---- close opposite bot positions (auto-reverse) -------------------
   if(hasBotPosition && botType != wantType && !CloseBotPositions())
      return;                          // never open if the close failed

   // ---- live CFD price on this chart (NOT the futures price) ---------
   double price = SymbolInfoDouble(_Symbol,
                                   (dir == "BUY") ? SYMBOL_ASK : SYMBOL_BID);
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   if(price <= 0 || point <= 0)
      return;

   // ---- SL/TP ---------------------------------------------------------
   double sl = 0.0, tp = 0.0;
   if(InpUseSignalSLTP)
     {
      double slPct = 0.0, tpPct = 0.0;
      if(GetValue(content, "sl_pct", s)) slPct = StringToDouble(s);
      if(GetValue(content, "tp_pct", s)) tpPct = StringToDouble(s);

      if(slPct > 0)
         sl = (dir == "BUY") ? price * (1.0 - slPct / 100.0)
                             : price * (1.0 + slPct / 100.0);
      if(tpPct > 0)
         tp = (dir == "BUY") ? price * (1.0 + tpPct / 100.0)
                             : price * (1.0 - tpPct / 100.0);

      // absolute fallbacks (only if percentages were not provided)
      if(sl <= 0 && GetValue(content, "sl", s)) sl = StringToDouble(s);
      if(tp <= 0 && GetValue(content, "tp", s)) tp = StringToDouble(s);

      if(sl <= 0)
         sl = (dir == "BUY") ? price - InpFallbackSL * point
                              : price + InpFallbackSL * point;
      if(tp <= 0)
         tp = (dir == "BUY") ? price + InpFallbackTP * point
                              : price - InpFallbackTP * point;
     }

   // ---- open the trade with YOUR lot size -----------------------------
   bool sent = false;
   if(dir == "BUY")
      sent = trade.Buy(InpManualLots, _Symbol, 0.0, sl, tp, "gold-bot BUY");
   else
      sent = trade.Sell(InpManualLots, _Symbol, 0.0, sl, tp, "gold-bot SELL");

   if(!sent)
     {
      Print("GoldTradingEA: order failed retcode=", trade.ResultRetcode(),
            " description=", trade.ResultRetcodeDescription());
      return;
     }

   PrintFormat("GoldTradingEA: %s %.2f lots @ %.2f (SL %.2f / TP %.2f, conf %.1f%%)",
               dir, InpManualLots, price, sl, tp, conf);
  }
//+------------------------------------------------------------------+
