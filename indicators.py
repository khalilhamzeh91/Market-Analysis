import pandas as pd
import config


def add_ema(df: pd.DataFrame, period: int) -> pd.DataFrame:
    df[f"ema_{period}"] = df["close"].ewm(span=period, adjust=False).mean()
    return df


def add_rsi(df: pd.DataFrame, period: int = config.RSI_PERIOD) -> pd.DataFrame:
    delta = df["close"].diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = -delta.clip(upper=0).rolling(period).mean()
    rs    = gain / loss
    df["rsi"] = 100 - (100 / (1 + rs))
    return df


def add_macd(df: pd.DataFrame,
             fast: int   = config.MACD_FAST,
             slow: int   = config.MACD_SLOW,
             signal: int = config.MACD_SIGNAL) -> pd.DataFrame:
    ema_fast         = df["close"].ewm(span=fast, adjust=False).mean()
    ema_slow         = df["close"].ewm(span=slow, adjust=False).mean()
    df["macd"]       = ema_fast - ema_slow
    df["macd_signal"]= df["macd"].ewm(span=signal, adjust=False).mean()
    df["macd_hist"]  = df["macd"] - df["macd_signal"]
    return df


def add_bollinger_bands(df: pd.DataFrame,
                        period: int = config.BB_PERIOD,
                        std: int    = config.BB_STD) -> pd.DataFrame:
    mid            = df["close"].rolling(period).mean()
    std_dev        = df["close"].rolling(period).std()
    df["bb_upper"] = mid + std * std_dev
    df["bb_mid"]   = mid
    df["bb_lower"] = mid - std * std_dev
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_mid"]
    return df


def add_atr(df: pd.DataFrame, period: int = config.ATR_PERIOD) -> pd.DataFrame:
    prev_close  = df["close"].shift(1)
    tr          = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"]  - prev_close).abs(),
    ], axis=1).max(axis=1)
    df["atr"]   = tr.rolling(period).mean()
    return df


def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = add_ema(df, config.EMA_FAST)
    df = add_ema(df, config.EMA_MID)
    df = add_ema(df, config.EMA_SLOW)
    df = add_rsi(df)
    df = add_macd(df)
    df = add_bollinger_bands(df)
    df = add_atr(df)
    return df


def extract_snapshot(df: pd.DataFrame) -> dict:
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last

    def v(col, decimals=2):
        val = last.get(col, float("nan"))
        return round(float(val), decimals) if pd.notna(val) else None

    # Detect MACD crossover in last 3 candles
    macd_cross = "NONE"
    if len(df) >= 4:
        recent = df.tail(4)
        for i in range(len(recent) - 1):
            m0, s0 = recent.iloc[i]["macd"], recent.iloc[i]["macd_signal"]
            m1, s1 = recent.iloc[i+1]["macd"], recent.iloc[i+1]["macd_signal"]
            if m0 < s0 and m1 > s1:
                macd_cross = "BULLISH"
            elif m0 > s0 and m1 < s1:
                macd_cross = "BEARISH"

    # BB position
    price    = v("close")
    bb_upper = v("bb_upper")
    bb_lower = v("bb_lower")
    bb_mid   = v("bb_mid")
    if price and bb_upper and bb_lower:
        range_ = bb_upper - bb_lower
        if range_ > 0:
            pct = (price - bb_lower) / range_
            bb_position = "UPPER" if pct > 0.7 else "LOWER" if pct < 0.3 else "MID"
        else:
            bb_position = "MID"
    else:
        bb_position = "MID"

    return {
        "price":       price,
        "ema_10":      v("ema_10"),
        "ema_50":      v("ema_50"),
        "ema_200":     v("ema_200"),
        "rsi":         v("rsi", 1),
        "macd":        v("macd", 4),
        "macd_signal": v("macd_signal", 4),
        "macd_hist":   v("macd_hist", 4),
        "bb_upper":    bb_upper,
        "bb_mid":      bb_mid,
        "bb_lower":    bb_lower,
        "bb_width":    v("bb_width", 4),
        "atr":         v("atr"),
        "macd_cross":  macd_cross,
        "bb_position": bb_position,
    }
