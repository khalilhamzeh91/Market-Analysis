import re
import json
import anthropic
import config
import data_fetcher
import indicators


def _ohlc_table(df, n: int) -> str:
    cols = ["time", "open", "high", "low", "close"]
    subset = df.tail(n)[cols].copy()
    subset["time"] = subset["time"].dt.strftime("%m-%d %H:%M")
    for c in ["open", "high", "low", "close"]:
        subset[c] = subset[c].round(2)
    return subset.to_string(index=False)


def build_analysis_prompt(symbol: str, mtf_data: dict, snapshots: dict) -> str:
    sections = []

    tf_descriptions = {
        "H4":  "(Structure & Major Trend)",
        "H1":  "(Intermediate Trend)",
        "M15": "(Entry Timing)",
        "M5":  "(Scalp / Precise Entry)",
    }
    for tf_label, n_candles in [("H4", 20), ("H1", 24), ("M15", 16), ("M5", 24)]:
        if tf_label not in mtf_data:
            continue
        df   = mtf_data[tf_label]
        snap = snapshots[tf_label]
        ohlc = _ohlc_table(df, n_candles)

        sections.append(f"""
### {tf_label} Timeframe {tf_descriptions.get(tf_label, "")}
Last {n_candles} candles (OHLC):
{ohlc}

{tf_label} Indicators (current values):
- Price: {snap['price']} | EMA 10: {snap['ema_10']} | EMA 50: {snap['ema_50']} | EMA 200: {snap['ema_200']}
- RSI 14: {snap['rsi']}
- MACD: {snap['macd']} | Signal: {snap['macd_signal']} | Histogram: {snap['macd_hist']}
- Bollinger Bands: Upper {snap['bb_upper']} | Mid {snap['bb_mid']} | Lower {snap['bb_lower']} | Width: {snap['bb_width']}
- ATR 14: {snap['atr']}
- MACD Crossover (last 3 bars): {snap['macd_cross']}
- BB Position: {snap['bb_position']}""")

    tf_data_str = "\n".join(sections)

    return f"""You are a professional gold (XAUUSD) market analyst. Analyze the data below and respond ONLY with a single valid JSON object — no markdown, no text before or after, just the JSON.

## Market Data — {symbol}
{tf_data_str}

Respond with this exact JSON structure (fill in real values from the data):

{{
  "price": 0000.00,
  "trend_overall": "BEARISH",
  "confidence": 75,
  "timeframes": [
    {{
      "tf": "H4",
      "label": "Macro / Structure",
      "trend": "BEARISH",
      "summary": "2-3 sentence analysis using actual price levels and indicator values"
    }},
    {{
      "tf": "H1",
      "label": "Intermediate",
      "trend": "BEARISH",
      "summary": "2-3 sentence analysis"
    }},
    {{
      "tf": "M15",
      "label": "Short-Term",
      "trend": "NEUTRAL",
      "summary": "2-3 sentence analysis"
    }},
    {{
      "tf": "M5",
      "label": "Intraday",
      "trend": "OVERSOLD",
      "summary": "2-3 sentence analysis"
    }}
  ],
  "levels": [
    {{"label": "Major Resistance", "price": "0000–0000", "type": "RESISTANCE"}},
    {{"label": "Near Resistance",  "price": "0000–0000", "type": "RESISTANCE"}},
    {{"label": "Current Price",    "price": "0000.00",   "type": "CURRENT"}},
    {{"label": "Immediate Support","price": "0000–0000", "type": "SUPPORT"}},
    {{"label": "Key Support Zone", "price": "0000–0000", "type": "SUPPORT"}}
  ],
  "scenarios": [
    {{"description": "scenario description → target", "probability": 50, "direction": "BEAR"}},
    {{"description": "scenario description → target", "probability": 30, "direction": "NEUTRAL"}},
    {{"description": "scenario description → target", "probability": 20, "direction": "BULL"}}
  ],
  "summary": "2-3 paragraph analyst summary. Be specific with price levels.",
  "tags": [
    {{"text": "Macro: Bearish", "type": "bear"}},
    {{"text": "Watch: 0000 support", "type": "bull"}}
  ],
  "recommendation": "SELL",
  "entry_zone": "0000–0000",
  "stop_loss": "0000",
  "target_1": "0000",
  "target_2": "0000",
  "risk_reward": "1:2.5"
}}

trend values allowed: BULLISH, BEARISH, NEUTRAL, OVERSOLD, OVERBOUGHT, RANGING
direction values allowed: BULL, BEAR, NEUTRAL
type (levels) values allowed: RESISTANCE, SUPPORT, CURRENT
recommendation values allowed: BUY, SELL, WAIT"""


def parse_analysis(raw: str) -> dict:
    default = {
        "price":          None,
        "trend_overall":  "NEUTRAL",
        "confidence":     50,
        "timeframes":     [],
        "levels":         [],
        "scenarios":      [],
        "summary":        raw,
        "tags":           [],
        "recommendation": "WAIT",
        "entry_zone":     "N/A",
        "stop_loss":      "N/A",
        "target_1":       "N/A",
        "target_2":       "N/A",
        "risk_reward":    "N/A",
        "full_analysis":  raw,
    }
    try:
        # Strip any accidental markdown fences
        clean = re.sub(r"```json|```", "", raw).strip()
        data  = json.loads(clean)
        default.update(data)
        default["full_analysis"] = raw
        # Back-compat keys
        default["confidence_score"]  = data.get("confidence", 50)
        default["confidence_reason"] = ""
    except (json.JSONDecodeError, Exception):
        pass
    return default


def analyze_symbol(symbol: str, mtf_data: dict, scan_data: dict) -> dict:
    snapshots = {}
    for tf_label, df_raw in mtf_data.items():
        df_ind = indicators.add_all_indicators(df_raw.copy())
        snapshots[tf_label] = indicators.extract_snapshot(df_ind)

    prompt = build_analysis_prompt(symbol, mtf_data, snapshots)

    client   = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model      = config.ANTHROPIC_MODEL,
        max_tokens = 2000,
        system     = (
            "You are a professional financial market analyst. "
            "Always respond with the exact section structure requested. "
            "Be specific with price levels. Never give generic advice."
        ),
        messages   = [{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text

    # Debug: save raw Claude response to file
    with open("C:/Users/khali/Documents/market_analysis_bot/debug_response.txt", "w", encoding="utf-8") as f:
        f.write(raw)

    parsed = parse_analysis(raw)

    return {**scan_data, "snapshots": snapshots, **parsed}


def analyze_top_symbols(scanner_results: list[dict], top_n: int = config.TOP_SYMBOLS_FOR_DEEP_ANALYSIS) -> list[dict]:
    analyses = []
    top      = scanner_results[:top_n]

    for i, entry in enumerate(top):
        symbol = entry["symbol"]
        print(f"  [{i+1}/{len(top)}] Deep analysis: {symbol}...")
        mtf_data = data_fetcher.fetch_multi_timeframe(symbol)
        if not mtf_data:
            print(f"    No data for {symbol}, skipping.")
            continue
        analysis = analyze_symbol(symbol, mtf_data, entry)
        analyses.append(analysis)

    return analyses
