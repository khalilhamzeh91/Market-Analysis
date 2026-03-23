import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
import config


def fetch_ohlcv(symbol: str, timeframe: int, count: int = config.CANDLE_COUNT) -> pd.DataFrame | None:
    mt5.symbol_select(symbol, True)
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
    if rates is None or len(rates) == 0:
        print(f"No data for {symbol}: {mt5.last_error()}")
        return None
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    return df


def fetch_multi_timeframe(symbol: str) -> dict[str, pd.DataFrame]:
    result = {}
    for label, tf in config.TIMEFRAMES.items():
        df = fetch_ohlcv(symbol, tf)
        if df is not None:
            result[label] = df
    return result


def fetch_open_positions() -> pd.DataFrame:
    positions = mt5.positions_get()
    if not positions:
        return pd.DataFrame()

    rows = []
    for p in positions:
        rows.append({
            "ticket":     p.ticket,
            "symbol":     p.symbol,
            "type":       "BUY" if p.type == mt5.ORDER_TYPE_BUY else "SELL",
            "volume":     p.volume,
            "open_price": p.price_open,
            "current":    p.price_current,
            "sl":         p.sl,
            "tp":         p.tp,
            "profit":     p.profit,
            "swap":       p.swap,
            "open_time":  datetime.fromtimestamp(p.time),
            "comment":    p.comment,
        })
    return pd.DataFrame(rows)


def fetch_trade_history(days_back: int = config.HISTORY_DAYS) -> pd.DataFrame:
    from_date = datetime.now() - timedelta(days=days_back)
    deals = mt5.history_deals_get(from_date, datetime.now())
    if deals is None or len(deals) == 0:
        return pd.DataFrame()

    df = pd.DataFrame([d._asdict() for d in deals])
    df["time"] = pd.to_datetime(df["time"], unit="s")

    # Keep only actual trade entries/exits (entry=1 in/out, not balance ops)
    df = df[df["symbol"] != ""]
    df = df[df["entry"].isin([0, 1])]  # 0=IN, 1=OUT

    # Match IN/OUT pairs by position_id
    rows = []
    for pos_id, group in df.groupby("position_id"):
        entries = group[group["entry"] == 0]
        exits   = group[group["entry"] == 1]
        if entries.empty or exits.empty:
            continue
        entry = entries.iloc[0]
        exit_ = exits.iloc[-1]
        profit = group["profit"].sum()
        rows.append({
            "ticket":      pos_id,
            "symbol":      entry["symbol"],
            "direction":   "BUY" if entry["type"] == mt5.ORDER_TYPE_BUY else "SELL",
            "open_time":   entry["time"],
            "close_time":  exit_["time"],
            "open_price":  entry["price"],
            "close_price": exit_["price"],
            "volume":      entry["volume"],
            "profit":      round(profit, 2),
            "swap":        round(group["swap"].sum(), 2),
            "commission":  round(group["commission"].sum(), 2),
        })

    return pd.DataFrame(rows) if rows else pd.DataFrame()
