import os
import MetaTrader5 as mt5

# --- SYMBOLS TO SCAN ---
SYMBOLS = [
    "XAUUSD_",
]

# --- TIMEFRAMES ---
TIMEFRAMES = {
    "M5":  mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "H1":  mt5.TIMEFRAME_H1,
    "H4":  mt5.TIMEFRAME_H4,
}

CANDLE_COUNT = 200

# --- INDICATOR PARAMETERS ---
EMA_FAST    = 10
EMA_MID     = 50
EMA_SLOW    = 200
RSI_PERIOD  = 14
MACD_FAST   = 12
MACD_SLOW   = 26
MACD_SIGNAL = 9
BB_PERIOD   = 20
BB_STD      = 2
ATR_PERIOD  = 14

# --- ANALYSIS ---
TOP_SYMBOLS_FOR_DEEP_ANALYSIS = 1
HISTORY_DAYS = 90

# --- CLAUDE ---
ANTHROPIC_MODEL   = "claude-opus-4-6"
ANTHROPIC_API_KEY = os.environ.get("API Key")

# --- OUTPUT ---
OUTPUT_DIR   = "C:/Users/khali/Documents/market_analysis_bot/output"
REPORT_FILE  = f"{OUTPUT_DIR}/market_analysis_report.html"
