import re
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

    return f"""You are a professional financial market analyst with deep expertise in technical analysis, price action, and multi-timeframe analysis. You are analyzing {symbol} for a real trading account.

## Market Data — {symbol}
{tf_data_str}

## Your Analysis Task

Provide a structured, professional market analysis covering ALL sections below. Be specific — use the actual price levels from the data.

### 1. TREND DIRECTION & STRENGTH
Analyze the trend on each timeframe separately. Are the EMAs aligned? Is there agreement across timeframes? Rate trend strength: Strong / Moderate / Weak / Ranging.

### 2. SUPPORT & RESISTANCE LEVELS
Identify 2-3 key support levels and 2-3 key resistance levels from the H4 data. Use swing highs/lows, EMA confluences, and Bollinger Band boundaries. Give specific price levels.

### 3. RSI INTERPRETATION
Interpret RSI on all three timeframes. Is there RSI divergence? What does momentum suggest for the next 4-8 hours?

### 4. MACD INTERPRETATION
Is MACD above or below zero? Recent crossover? Histogram expanding or contracting? Does this confirm or contradict price trend?

### 5. BOLLINGER BAND ANALYSIS
Where is price relative to the bands on each timeframe? Is volatility expanding or contracting? Band squeeze forming? Is price walking the bands or mean-reverting?

### 6. MARKET SENTIMENT & CONTEXT
Based purely on the technical picture: accumulation or distribution? Trending or ranging market? High-conviction setup or wait-and-see?

### 7. SHORT-TERM OUTLOOK (next 4-8 hours / M15-H1)
Most probable price path. Give a likely price range. What confirms this view? What invalidates it?

### 8. MEDIUM-TERM OUTLOOK (next 1-3 days / H4)
Directional bias. Where could price realistically reach? Any key levels that change the picture?

### 9. TRADING RECOMMENDATION
BUY / SELL / WAIT
- Entry zone: [price range]
- Stop loss: [price level and reasoning]
- Target 1: [price level]
- Target 2: [price level]
- Risk/Reward ratio: [calculated]
- If WAIT: what condition must be met before entry is justified?

### 10. CRITICAL LEVELS NOW
List exactly 4-6 key price levels that matter RIGHT NOW. For each level provide its current status.
Use ONLY these status values: BROKEN_RESISTANCE | BEING_TESTED | SUPPORT | RESISTANCE | RECENT_LOW | RECENT_HIGH | PSYCHOLOGICAL
Format each line EXACTLY like this:
LEVEL: [price] | STATUS: [status] | NOTE: [short description]

Example:
LEVEL: 3245.00 | STATUS: BEING_TESTED | NOTE: Key intraday support being tested now
LEVEL: 3280.00 | STATUS: RESISTANCE | NOTE: H4 resistance confluence with EMA 50

### 11. SCENARIO PROBABILITIES
Give 2-3 most probable scenarios RIGHT NOW with a percentage probability each (must sum to 100%).
Format EXACTLY like this:
SCENARIO: [description] | PROBABILITY: [number]%

Example:
SCENARIO: Bounce from 3245 back to 3280 | PROBABILITY: 55%
SCENARIO: Break below 3245 towards 3210 | PROBABILITY: 45%

### 12. CONFIDENCE SCORE
Rate your confidence 0-100:
- 90-100: All timeframes aligned, clear setup
- 70-89: Good setup with minor conflicting signals
- 50-69: Mixed signals, confirmation needed
- Below 50: Too uncertain, do not trade

Confidence Score: [NUMBER]/100
Primary reason: [one sentence]

Be analytical, not generic. Reference actual price levels."""


def parse_analysis(raw: str) -> dict:
    result = {
        "recommendation":   "WAIT",
        "entry_zone":       "N/A",
        "stop_loss":        "N/A",
        "target_1":         "N/A",
        "target_2":         "N/A",
        "risk_reward":      "N/A",
        "confidence_score": 50,
        "confidence_reason":"",
        "critical_levels":  [],
        "scenarios":        [],
        "full_analysis":    raw,
    }

    # Confidence score
    m = re.search(r"Confidence Score[:\s]+(\d{1,3})\s*/\s*100", raw, re.IGNORECASE)
    if m:
        result["confidence_score"] = int(m.group(1))

    # Primary reason
    m = re.search(r"Primary reason[:\s]+(.+)", raw, re.IGNORECASE)
    if m:
        result["confidence_reason"] = m.group(1).strip()

    # Recommendation
    m = re.search(r"(?:TRADING RECOMMENDATION|Recommendation)[^\n]*\n+\s*(BUY|SELL|WAIT)", raw, re.IGNORECASE)
    if m:
        result["recommendation"] = m.group(1).upper()
    else:
        # Fallback: look for standalone BUY/SELL/WAIT near recommendation section
        m = re.search(r"###\s*9\..*?(?:^|\n)\s*(BUY|SELL|WAIT)\b", raw, re.IGNORECASE | re.DOTALL)
        if m:
            result["recommendation"] = m.group(1).upper()

    # Entry zone
    m = re.search(r"Entry zone[:\s]+([^\n]+)", raw, re.IGNORECASE)
    if m:
        result["entry_zone"] = m.group(1).strip()

    # Stop loss
    m = re.search(r"Stop loss[:\s]+([^\n]+)", raw, re.IGNORECASE)
    if m:
        result["stop_loss"] = m.group(1).strip()

    # Target 1
    m = re.search(r"Target 1[:\s]+([^\n]+)", raw, re.IGNORECASE)
    if m:
        result["target_1"] = m.group(1).strip()

    # Target 2
    m = re.search(r"Target 2[:\s]+([^\n]+)", raw, re.IGNORECASE)
    if m:
        result["target_2"] = m.group(1).strip()

    # Risk/reward
    m = re.search(r"Risk[/\\]Reward[:\s]+([^\n]+)", raw, re.IGNORECASE)
    if m:
        result["risk_reward"] = m.group(1).strip()

    # Critical levels
    levels = []
    for m in re.finditer(r"LEVEL:\s*([\d.,]+)\s*\|\s*STATUS:\s*(\w+)\s*\|\s*NOTE:\s*([^\n]+)", raw, re.IGNORECASE):
        levels.append({
            "price":  m.group(1).strip(),
            "status": m.group(2).strip().upper(),
            "note":   m.group(3).strip(),
        })
    result["critical_levels"] = levels

    # Scenarios
    scenarios = []
    for m in re.finditer(r"SCENARIO:\s*([^|]+)\|\s*PROBABILITY:\s*(\d+)%", raw, re.IGNORECASE):
        scenarios.append({
            "description": m.group(1).strip(),
            "probability": int(m.group(2)),
        })
    result["scenarios"] = scenarios

    return result


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
