//+------------------------------------------------------------------+
//|                                        GoldSignalIndicator.mq5    |
//|   Gold Trading System - MT5 indicator  v1.70                      |
//|                                                                   |
//|   Reads gold_signal.txt and draws a BIG label in the BOTTOM-RIGHT |
//|   corner (visible on black charts):                               |
//|     BUY  (bright green) / SELL (red) / NEUTRAL (white)            |
//|   plus the confidence % and news state. Also draws arrows.        |
//+------------------------------------------------------------------+
#property copyright "Gold Trading System"
#property version   "1.90"
#property strict
#property indicator_chart_window

#property indicator_buffers 1
#property indicator_plots   1
#property indicator_type1   DRAW_NONE
#property indicator_label1  "GoldSignal"

input string InpSignalFile = "gold_signal.txt"; // Signal file name
input color  InpBuyColor   = clrLime;           // Buy arrow colour
input color  InpSellColor  = clrRed;            // Sell arrow colour

double   g_dummyBuffer[];       // required by MQL5 (not drawn)
datetime g_lastSignalId = 0;
string   g_lastLogged   = "";

//+------------------------------------------------------------------+
int OnInit()
  {
   SetIndexBuffer(0, g_dummyBuffer, INDICATOR_DATA);
   DrawLabel("GoldSignal ready...", clrWhite, clrDimGray);
   Print("GoldSignalIndicator v1.90 attached. Reading file: ", InpSignalFile);
   EventSetTimer(1);
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   EventKillTimer();
  }

//+------------------------------------------------------------------+
int OnCalculate(const int rates_total,
                const int prev_calculated,
                const datetime &time[],
                const double &open[],
                const double &high[],
                const double &low[],
                const double &close[],
                const long &tick_volume[],
                const long &volume[],
                const int &spread[])
  {
   return(rates_total);
  }

//+------------------------------------------------------------------+
void OnTimer()
  {
   string content = ReadSignalFile();

   if(content == "")
     {
      DrawLabel("waiting for signal file...", clrWhite, clrDimGray);
      LogOnce("GoldSignalIndicator: no signal file found.");
      return;
     }

   string s;
   if(!GetValue(content, "id", s))
     {
      DrawLabel("signal file unreadable", clrWhite, clrDimGray);
      LogOnce("GoldSignalIndicator: FILE CONTENT (raw): [" +
              StringSubstr(content, 0, 250) + "]");
      return;
     }
   datetime sigId = (datetime)StringToInteger(s);

   string dir = "";
   GetValue(content, "direction", dir);
   double conf = 0.0;
   if(GetValue(content, "confidence", s))
      conf = StringToDouble(s);
   string news = "";
   GetValue(content, "news_state", news);

   // bright colours that stand out on a BLACK chart
   color labelColor = clrWhite;      // neutral
   color bgColor    = clrDimGray;    // visible box on black
   if(dir == "BUY")
     {
      labelColor = clrLime;
      bgColor    = clrDarkGreen;
     }
   else if(dir == "SELL")
     {
      labelColor = clrOrange;
      bgColor    = clrDarkRed;
     }

   string display = StringFormat("%s  %.0f%%", 
                                 (dir == "" ? "NO SIGNAL" : dir),
                                 conf);

   DrawLabel(display, labelColor, bgColor);
   LogOnce("GoldSignalIndicator: " + display + " [" +
           (news == "" ? "QUIET" : news) + "]");

   if((dir == "BUY" || dir == "SELL") && sigId != g_lastSignalId)
     {
      g_lastSignalId = sigId;
      string arrowName = "GoldSignalArrow_" + IntegerToString(sigId);
      double price = 0.0;
      if(GetValue(content, "price", s))
         price = StringToDouble(s);
      if(price <= 0)
         price = (dir == "BUY") ? SymbolInfoDouble(_Symbol, SYMBOL_BID)
                                : SymbolInfoDouble(_Symbol, SYMBOL_ASK);

      ObjectCreate(0, arrowName, OBJ_ARROW, 0, TimeCurrent(), price);
      ObjectSetInteger(0, arrowName, OBJPROP_ARROWCODE,
                       (dir == "BUY") ? 233 : 234);
      ObjectSetInteger(0, arrowName, OBJPROP_COLOR,
                       (dir == "BUY") ? InpBuyColor : InpSellColor);
      ObjectSetInteger(0, arrowName, OBJPROP_WIDTH, 3);
     }
  }

//+------------------------------------------------------------------+
//| Draw a label in the BOTTOM-LEFT corner with a fixed-size box.     |
//| Bottom-left is the only corner with no axis/toolbar, so it is     |
//| fully visible on ANY screen size or resolution.                   |
//+------------------------------------------------------------------+
void DrawLabel(string text, color clr, color bg)
  {
   ObjectCreate(0, "GoldSignalLabel", OBJ_LABEL, 0, 0, 0);
   ObjectSetInteger(0, "GoldSignalLabel", OBJPROP_CORNER, CORNER_LEFT_LOWER);
   ObjectSetInteger(0, "GoldSignalLabel", OBJPROP_XDISTANCE, 25);
   ObjectSetInteger(0, "GoldSignalLabel", OBJPROP_YDISTANCE, 25);
   ObjectSetInteger(0, "GoldSignalLabel", OBJPROP_FONTSIZE, 11);
   ObjectSetInteger(0, "GoldSignalLabel", OBJPROP_COLOR, clr);
   ObjectSetInteger(0, "GoldSignalLabel", OBJPROP_BGCOLOR, bg);
   ObjectSetInteger(0, "GoldSignalLabel", OBJPROP_BORDER_TYPE, BORDER_FLAT);
   ObjectSetInteger(0, "GoldSignalLabel", OBJPROP_BACK, true);
   ObjectSetInteger(0, "GoldSignalLabel", OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, "GoldSignalLabel", OBJPROP_HIDDEN, false);
   ObjectSetString(0, "GoldSignalLabel", OBJPROP_TEXT, text);
  }

//+------------------------------------------------------------------+
void LogOnce(string text)
  {
   if(text != g_lastLogged)
     {
      g_lastLogged = text;
      Print(text);
     }
  }

//+------------------------------------------------------------------+
//| Read the signal file with FILE_ANSI (the bot writes plain ASCII). |
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
bool GetValue(string content, string key, string &value)
  {
   string lines[];
   int n = StringSplit(content, '\n', lines);
   for(int i = 0; i < n; i++)
     {
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
