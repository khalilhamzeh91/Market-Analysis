import MetaTrader5 as mt5
import pandas as pd
import config
import data_fetcher
import indicators


def _score_trend(snap: dict) -> tuple[int, str]:
    e10, e50, e200 = snap["ema_10"], snap["ema_50"], snap["ema_200"]
    if None in (e10, e50, e200):
        return 0, "NEUTRAL"

    if e10 > e50 > e200:
        return 25, "STRONG_UP"
    if e10 < e50 < e200:
        return 25, "STRONG_DOWN"
    if e10 > e50 and e50 > e200 * 0.995:
        return 15, "WEAK_UP"
    if e10 < e50 and e50 < e200 * 1.005:
        return 15, "WEAK_DOWN"
    return 5, "NEUTRAL"


def _score_momentum(snap: dict, trend: str) -> int:
    rsi      = snap["rsi"]
    macd_h   = snap["macd_hist"]
    if rsi is None:
        return 0

    score = 0
    if trend in ("STRONG_UP", "WEAK_UP"):
        if 40 <= rsi <= 60:
            score += 20
        elif 60 < rsi <= 70:
            score += 25
        elif rsi > 75:
            score += 3
        else:
            score += 10
    elif trend in ("STRONG_DOWN", "WEAK_DOWN"):
        if 40 <= rsi <= 60:
            score += 20
        elif 30 <= rsi < 40:
            score += 25
        elif rsi < 25:
            score += 3
        else:
            score += 10
    else:
        score += 5

    if macd_h is not None:
        prev_snap_hist = snap.get("macd_hist_prev")
        if prev_snap_hist is not None and abs(macd_h) > abs(prev_snap_hist):
            score = min(score + 5, 25)

    return min(score, 25)


def _score_volatility(snap: dict, df: pd.DataFrame) -> int:
    atr     = snap["atr"]
    bb_w    = snap["bb_width"]
    if atr is None or df is None or len(df) < 20:
        return 5

    avg_atr = df["atr"].tail(20).mean()
    score   = 0
    if avg_atr > 0:
        ratio = atr / avg_atr
        if ratio > 1.2:
            score += 20
        elif ratio > 0.9:
            score += 12
        else:
            score += 3

    if bb_w is not None:
        avg_bbw = df["bb_width"].tail(20).mean()
        if pd.notna(avg_bbw) and avg_bbw > 0 and bb_w > avg_bbw:
            score = min(score + 5, 25)

    return min(score, 25)


def _score_setup(snap: dict, trend: str) -> int:
    bp          = snap["bb_position"]
    macd_cross  = snap["macd_cross"]
    score       = 0

    if trend in ("STRONG_UP", "WEAK_UP") and bp == "LOWER":
        score += 20
    elif trend in ("STRONG_DOWN", "WEAK_DOWN") and bp == "UPPER":
        score += 20
    elif bp == "MID":
        score += 8
    else:
        score += 5

    if macd_cross in ("BULLISH", "BEARISH"):
        score = min(score + 5, 25)

    return min(score, 25)


def score_symbol(symbol: str) -> dict | None:
    df_raw = data_fetcher.fetch_ohlcv(symbol, mt5.TIMEFRAME_M15)
    if df_raw is None:
        return None

    df = indicators.add_all_indicators(df_raw.copy())
    snap = indicators.extract_snapshot(df)

    # Add prev macd_hist for momentum delta
    if len(df) > 1:
        snap["macd_hist_prev"] = df.iloc[-2].get("macd_hist")

    trend_score, trend_label = _score_trend(snap)
    momentum_score  = _score_momentum(snap, trend_label)
    volatility_score= _score_volatility(snap, df)
    setup_score     = _score_setup(snap, trend_label)

    total = trend_score + momentum_score + volatility_score + setup_score

    direction = "NEUTRAL"
    if trend_label in ("STRONG_UP", "WEAK_UP"):
        direction = "BULLISH"
    elif trend_label in ("STRONG_DOWN", "WEAK_DOWN"):
        direction = "BEARISH"

    return {
        "symbol":      symbol,
        "score":       total,
        "direction":   direction,
        "trend":       trend_label,
        "price":       snap["price"],
        "rsi":         snap["rsi"],
        "atr":         snap["atr"],
        "macd_cross":  snap["macd_cross"],
        "bb_position": snap["bb_position"],
        "ema_10":      snap["ema_10"],
        "ema_50":      snap["ema_50"],
        "ema_200":     snap["ema_200"],
    }


def scan_all_symbols() -> list[dict]:
    results = []
    for symbol in config.SYMBOLS:
        print(f"  Scanning {symbol}...")
        result = score_symbol(symbol)
        if result:
            results.append(result)

    results.sort(key=lambda x: x["score"], reverse=True)
    return results
