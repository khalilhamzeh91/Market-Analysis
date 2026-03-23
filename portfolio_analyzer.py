import pandas as pd
from datetime import datetime


def analyze_open_positions(positions_df: pd.DataFrame, account: dict) -> dict:
    if positions_df.empty:
        return {
            "positions": [],
            "total_unrealized_pnl": 0.0,
            "float_pct": 0.0,
            "total_risk_exposure_usd": 0.0,
            "total_risk_pct": 0.0,
            "long_count": 0,
            "short_count": 0,
            "position_count": 0,
            "total_volume": 0.0,
            "long_volume": 0.0,
            "short_volume": 0.0,
            "total_swap": 0.0,
            "exposure_bias": "NEUTRAL",
            "suggestions": [],
        }

    balance  = account.get("balance", 1)
    now      = datetime.now()
    rows     = []
    total_risk_usd = 0.0
    suggestions    = []

    symbol_dirs: dict[str, list] = {}

    for _, p in positions_df.iterrows():
        entry = p["open_price"]
        sl    = p["sl"]
        vol   = p["volume"]
        risk_usd = abs(entry - sl) * vol * 100 if sl != 0 else 0
        risk_pct = (risk_usd / balance * 100) if balance > 0 else 0
        duration = now - p["open_time"]
        hours    = duration.total_seconds() / 3600

        rows.append({
            "ticket":    p["ticket"],
            "symbol":    p["symbol"],
            "type":      p["type"],
            "volume":    p["volume"],
            "open_price":p["open_price"],
            "current":   p["current"],
            "sl":        p["sl"],
            "tp":        p["tp"],
            "profit":    p["profit"],
            "swap":      p["swap"],
            "risk_usd":  round(risk_usd, 2),
            "risk_pct":  round(risk_pct, 2),
            "duration_h":round(hours, 1),
        })
        total_risk_usd += risk_usd

        if risk_pct > 2:
            suggestions.append(
                f"Position #{p['ticket']} ({p['symbol']} {p['type']}) carries {risk_pct:.1f}% account risk — above the 2% rule."
            )

        if hours > 48 and p["profit"] < 0:
            suggestions.append(
                f"Position #{p['ticket']} ({p['symbol']}) has been losing for {hours:.0f} hours. Review if the thesis is still valid."
            )

        dirs = symbol_dirs.setdefault(p["symbol"], [])
        dirs.append(p["type"])

    for symbol, dirs in symbol_dirs.items():
        if "BUY" in dirs and "SELL" in dirs:
            suggestions.append(
                f"Opposing positions on {symbol} detected — this creates a locked trade. Review your intent."
            )

    total_risk_pct = (total_risk_usd / balance * 100) if balance > 0 else 0
    if total_risk_pct > 5:
        suggestions.append(
            f"Total open risk is {total_risk_pct:.1f}% of balance (${total_risk_usd:.2f}). Consider reducing exposure."
        )

    total_pnl = positions_df["profit"].sum()
    if balance > 0 and total_pnl < -(balance * 0.03):
        suggestions.append(
            f"Open drawdown is ${abs(total_pnl):.2f} ({abs(total_pnl)/balance*100:.1f}% of balance). Risk management review recommended."
        )

    long_count   = len(positions_df[positions_df["type"] == "BUY"])
    short_count  = len(positions_df[positions_df["type"] == "SELL"])
    total_volume = round(positions_df["volume"].sum(), 2)
    long_volume  = round(positions_df[positions_df["type"] == "BUY"]["volume"].sum(), 2)
    short_volume = round(positions_df[positions_df["type"] == "SELL"]["volume"].sum(), 2)
    total_swap   = round(positions_df["swap"].sum(), 2)

    # Exposure bias
    if long_volume > short_volume:
        bias = f"NET LONG {round(long_volume - short_volume, 2)} lots"
    elif short_volume > long_volume:
        bias = f"NET SHORT {round(short_volume - long_volume, 2)} lots"
    else:
        bias = "NEUTRAL (hedged)"

    # Floating P/L as % of balance
    float_pct = round(total_pnl / balance * 100, 2) if balance > 0 else 0

    return {
        "positions":              rows,
        "total_unrealized_pnl":   round(total_pnl, 2),
        "float_pct":              float_pct,
        "total_risk_exposure_usd":round(total_risk_usd, 2),
        "total_risk_pct":         round(total_risk_pct, 2),
        "long_count":             long_count,
        "short_count":            short_count,
        "position_count":         len(rows),
        "total_volume":           total_volume,
        "long_volume":            long_volume,
        "short_volume":           short_volume,
        "total_swap":             total_swap,
        "exposure_bias":          bias,
        "suggestions":            suggestions,
    }


def analyze_trade_history(history_df: pd.DataFrame) -> dict:
    if history_df.empty:
        return {
            "total_trades": 0,
            "wins": 0, "losses": 0, "win_rate": 0.0,
            "profit_factor": 0.0, "avg_win": 0.0, "avg_loss": 0.0,
            "expectancy": 0.0, "total_profit": 0.0,
            "max_consecutive_wins": 0, "max_consecutive_losses": 0,
            "best_trade": None, "worst_trade": None,
            "by_symbol": [], "by_hour": [], "by_day": [],
            "recent_10_win_rate": 0.0,
            "performance_trend": "STABLE",
            "patterns": [],
            "trades": [],
        }

    df = history_df.copy()
    df["is_win"] = df["profit"] > 0

    wins   = df[df["is_win"]]
    losses = df[~df["is_win"]]
    total  = len(df)

    win_rate     = len(wins) / total * 100 if total > 0 else 0
    gross_win    = wins["profit"].sum() if not wins.empty else 0
    gross_loss   = abs(losses["profit"].sum()) if not losses.empty else 1
    profit_factor= round(gross_win / gross_loss, 2) if gross_loss > 0 else 0
    avg_win      = round(wins["profit"].mean(), 2) if not wins.empty else 0
    avg_loss     = round(losses["profit"].mean(), 2) if not losses.empty else 0
    expectancy   = round((win_rate / 100 * avg_win) + ((1 - win_rate / 100) * avg_loss), 2)
    total_profit = round(df["profit"].sum(), 2)

    # Consecutive streaks
    max_consec_wins = max_consec_losses = cur_w = cur_l = 0
    for _, row in df.sort_values("close_time").iterrows():
        if row["is_win"]:
            cur_w += 1
            cur_l  = 0
        else:
            cur_l += 1
            cur_w  = 0
        max_consec_wins   = max(max_consec_wins, cur_w)
        max_consec_losses = max(max_consec_losses, cur_l)

    best_trade  = df.loc[df["profit"].idxmax()].to_dict() if not df.empty else None
    worst_trade = df.loc[df["profit"].idxmin()].to_dict() if not df.empty else None

    # Per-symbol breakdown
    by_symbol = []
    for sym, grp in df.groupby("symbol"):
        w = grp["profit"] > 0
        by_symbol.append({
            "symbol":       sym,
            "trades":       len(grp),
            "wins":         w.sum(),
            "win_rate":     round(w.mean() * 100, 1),
            "total_profit": round(grp["profit"].sum(), 2),
        })
    by_symbol.sort(key=lambda x: x["total_profit"], reverse=True)

    # By hour
    df["hour"] = pd.to_datetime(df["open_time"]).dt.hour
    by_hour = []
    for h, grp in df.groupby("hour"):
        w = grp["profit"] > 0
        by_hour.append({"hour": int(h), "trades": len(grp), "win_rate": round(w.mean() * 100, 1)})
    by_hour.sort(key=lambda x: x["hour"])

    # By day of week
    df["dow"] = pd.to_datetime(df["open_time"]).dt.day_name()
    by_day = []
    for day, grp in df.groupby("dow"):
        w = grp["profit"] > 0
        by_day.append({"day": day, "trades": len(grp), "win_rate": round(w.mean() * 100, 1)})

    # Recent 10
    recent_10 = df.sort_values("close_time").tail(10)
    recent_wr  = round((recent_10["profit"] > 0).mean() * 100, 1) if not recent_10.empty else 0

    if recent_wr > win_rate + 10:
        perf_trend = "IMPROVING"
    elif recent_wr < win_rate - 10:
        perf_trend = "DECLINING"
    else:
        perf_trend = "STABLE"

    # Pattern observations
    patterns = []
    if by_symbol:
        best_sym = max(by_symbol, key=lambda x: x["win_rate"])
        patterns.append(f"Best performing symbol: {best_sym['symbol']} with {best_sym['win_rate']}% win rate over {best_sym['trades']} trades.")

    if avg_win > 0 and avg_loss < 0:
        ratio = abs(avg_win / avg_loss)
        patterns.append(f"Average win (${avg_win:.2f}) is {ratio:.1f}x your average loss (${abs(avg_loss):.2f}) — {'positive' if ratio > 1 else 'negative'} R:R edge.")

    if by_hour:
        best_hour = max(by_hour, key=lambda x: x["win_rate"] if x["trades"] >= 2 else 0)
        patterns.append(f"Best win rate by hour: {best_hour['hour']:02d}:00 UTC ({best_hour['win_rate']}% across {best_hour['trades']} trades).")

    patterns.append(f"Recent 10 trades: {recent_wr}% win rate vs overall {win_rate:.1f}% — performance is {perf_trend}.")

    if max_consec_losses >= 3:
        patterns.append(f"Maximum consecutive losses: {max_consec_losses}. Watch for revenge trading after loss streaks.")

    return {
        "total_trades":          total,
        "wins":                  len(wins),
        "losses":                len(losses),
        "win_rate":              round(win_rate, 1),
        "profit_factor":         profit_factor,
        "avg_win":               avg_win,
        "avg_loss":              avg_loss,
        "expectancy":            expectancy,
        "total_profit":          total_profit,
        "max_consecutive_wins":  max_consec_wins,
        "max_consecutive_losses":max_consec_losses,
        "best_trade":            best_trade,
        "worst_trade":           worst_trade,
        "by_symbol":             by_symbol,
        "by_hour":               by_hour,
        "by_day":                by_day,
        "recent_10_win_rate":    recent_wr,
        "performance_trend":     perf_trend,
        "patterns":              patterns,
        "trades":                df.sort_values("close_time", ascending=False).head(50).to_dict("records"),
    }
