from datetime import datetime
import re


# ── helpers ──────────────────────────────────────────────────────────────────

def _pnl_color(value):
    if value is None:
        return "#ffffff"
    return "#c8f7c5" if value > 0 else "#f7c5c5" if value < 0 else "#ffffff"


def _badge(text: str, color: str) -> str:
    return f'<span style="background:{color};color:#fff;padding:2px 8px;border-radius:12px;font-size:12px;font-weight:600">{text}</span>'


def _direction_badge(direction: str) -> str:
    colors = {"BULLISH": "#00b894", "BEARISH": "#d63031", "NEUTRAL": "#636e72"}
    return _badge(direction, colors.get(direction, "#636e72"))


def _rec_badge(rec: str) -> str:
    colors = {"BUY": "#00b894", "SELL": "#d63031", "WAIT": "#fdcb6e"}
    color  = colors.get(rec, "#636e72")
    return f'<span style="background:{color};color:{"#000" if rec=="WAIT" else "#fff"};padding:4px 14px;border-radius:4px;font-size:14px;font-weight:700">{rec}</span>'


def _score_bar(score: int) -> str:
    color = "#00b894" if score >= 70 else "#fdcb6e" if score >= 50 else "#d63031"
    return f'''<div style="background:#e0e0e0;border-radius:4px;height:8px;width:100%">
      <div style="width:{score}%;background:{color};height:8px;border-radius:4px"></div>
    </div>'''


def _confidence_bar(score: int) -> str:
    color = "#00b894" if score >= 70 else "#fdcb6e" if score >= 50 else "#d63031"
    filled = "■" * (score // 10)
    empty  = "□" * (10 - score // 10)
    return f'<span style="color:{color};font-size:16px">{filled}</span><span style="color:#ccc;font-size:16px">{empty}</span> <b>{score}/100</b>'


def _card(title: str, value: str, sub: str = "", color: str = "#2c7be5") -> str:
    return f'''<div style="background:white;padding:14px 20px;border-radius:8px;box-shadow:0 2px 6px #ccc;text-align:center;min-width:110px">
      <div style="font-size:24px;font-weight:700;color:{color}">{value}</div>
      <div style="font-size:12px;color:#888;margin-top:2px">{title}</div>
      {f'<div style="font-size:11px;color:#aaa">{sub}</div>' if sub else ""}
    </div>'''


def _section_title(title: str) -> str:
    return f'<h2 style="color:#1a1a2e;border-left:4px solid #2c7be5;padding-left:12px;margin:30px 0 16px">{title}</h2>'


def _format_analysis_text(raw: str) -> str:
    """Convert Claude's markdown-style sections to simple HTML."""
    html = raw
    html = re.sub(r"###\s*\d+\.\s*(.+)", r"<h4 style='color:#2c7be5;margin-top:16px'>\1</h4>", html)
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)
    html = html.replace("\n\n", "</p><p>").replace("\n", "<br>")
    return f"<p>{html}</p>"


# ── CSS ───────────────────────────────────────────────────────────────────────

CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: Arial, sans-serif; background: #f0f2f5; color: #333; }
.wrap { max-width: 1300px; margin: 0 auto; padding: 0 16px 40px; }
.header { background: linear-gradient(135deg,#1a1a2e,#16213e); color: white; padding: 28px 32px; margin-bottom: 24px; }
.header h1 { font-size: 28px; margin-bottom: 6px; }
.header p  { color: #aab; font-size: 14px; }
.cards-row { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 20px; }
.panel { background: white; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,.08); padding: 24px; margin-bottom: 20px; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { background: #2c7be5; color: white; padding: 10px 8px; text-align: left; }
td { padding: 8px; border-bottom: 1px solid #eee; vertical-align: top; }
tr:hover td { background: #f8f9ff; }
.suggestion-box { background: #fff8e1; border-left: 4px solid #fdcb6e; padding: 12px 16px; border-radius: 4px; margin-top: 16px; }
.suggestion-box li { margin: 6px 0; font-size: 13px; }
.pattern-box { background: #e8f4fd; border-left: 4px solid #2c7be5; padding: 12px 16px; border-radius: 4px; margin-top: 16px; }
.pattern-box li { margin: 6px 0; font-size: 13px; }
.rec-box { border: 2px solid #e0e0e0; border-radius: 8px; padding: 16px; margin: 16px 0; }
.snap-table td, .snap-table th { padding: 5px 8px; font-size: 12px; }
.snap-table th { background: #f0f2f5; color: #555; }
details summary { cursor: pointer; color: #2c7be5; font-weight: 600; font-size: 13px; margin-top: 12px; }
details[open] summary { margin-bottom: 10px; }
.rank-1 td:first-child { font-weight: 700; color: #fdcb6e; }
"""

# ── sections ─────────────────────────────────────────────────────────────────

def render_header(account: dict, timestamp: str) -> str:
    bal = account.get("balance", 0)
    eq  = account.get("equity", 0)
    ml  = account.get("margin_level", 0)
    return f'''<div class="header">
  <div class="wrap">
    <h1>AI Market Analysis Report</h1>
    <p>Account: <b>{account.get("login","—")}</b> &nbsp;|&nbsp;
       Balance: <b>${bal:,.2f}</b> &nbsp;|&nbsp;
       Equity: <b>${eq:,.2f}</b> &nbsp;|&nbsp;
       Margin Level: <b>{ml:.1f}%</b> &nbsp;|&nbsp;
       Server: <b>{account.get("server","—")}</b> &nbsp;|&nbsp;
       Updated: <b>{timestamp}</b></p>
  </div>
</div>'''


def render_scanner(scanner_results: list) -> str:
    top = scanner_results[0]["symbol"] if scanner_results else "—"
    top_score = scanner_results[0]["score"] if scanner_results else 0

    rows = ""
    for i, r in enumerate(scanner_results):
        rank_class = "rank-1" if i == 0 else ""
        mc_color   = {"BULLISH":"#00b894","BEARISH":"#d63031","NONE":"#aaa"}.get(r.get("macd_cross","NONE"),"#aaa")
        bp_color   = {"UPPER":"#d63031","LOWER":"#00b894","MID":"#aaa"}.get(r.get("bb_position","MID"),"#aaa")
        rows += f'''<tr class="{rank_class}">
          <td>#{i+1}</td>
          <td><b>{r["symbol"]}</b></td>
          <td>
            {_score_bar(r["score"])}
            <span style="font-size:12px;color:#555">{r["score"]}/100</span>
          </td>
          <td>{_direction_badge(r["direction"])}</td>
          <td><span style="font-size:12px">{r.get("trend","—").replace("_"," ")}</span></td>
          <td>{r.get("price","—")}</td>
          <td>{r.get("rsi","—")}</td>
          <td>{_badge(r.get("macd_cross","NONE"), mc_color)}</td>
          <td>{_badge(r.get("bb_position","—"), bp_color)}</td>
        </tr>'''

    return f'''
{_section_title(f"Market Scanner — {len(scanner_results)} Symbols | Top: {top} ({top_score}/100)")}
<div class="panel">
  <table>
    <tr>
      <th>Rank</th><th>Symbol</th><th style="min-width:120px">Score</th>
      <th>Direction</th><th>Trend</th><th>Price</th>
      <th>RSI</th><th>MACD Cross</th><th>BB Position</th>
    </tr>
    {rows}
  </table>
</div>'''


def render_analysis_card(a: dict, idx: int) -> str:
    symbol   = a["symbol"]
    score    = a.get("score", 0)
    direction= a.get("direction", "NEUTRAL")
    trend    = a.get("trend", "—").replace("_", " ")
    conf     = a.get("confidence_score", 50)
    rec      = a.get("recommendation", "WAIT")
    snaps    = a.get("snapshots", {})

    # Indicator snapshot table
    tf_labels = [tf for tf in ["M5", "M15", "H1", "H4"] if tf in snaps]
    header_row = "<th>Indicator</th>" + "".join(f"<th>{tf}</th>" for tf in tf_labels)
    fields = [
        ("Price",      "price"),
        ("EMA 10",     "ema_10"),
        ("EMA 50",     "ema_50"),
        ("EMA 200",    "ema_200"),
        ("RSI 14",     "rsi"),
        ("MACD",       "macd"),
        ("MACD Sig",   "macd_signal"),
        ("MACD Hist",  "macd_hist"),
        ("BB Upper",   "bb_upper"),
        ("BB Mid",     "bb_mid"),
        ("BB Lower",   "bb_lower"),
        ("ATR 14",     "atr"),
    ]
    snap_rows = ""
    for label, key in fields:
        vals = "".join(f"<td>{snaps[tf].get(key,'—')}</td>" for tf in tf_labels)
        snap_rows += f"<tr><td><b>{label}</b></td>{vals}</tr>"

    snap_table = f'''<table class="snap-table" style="margin:16px 0">
      <tr>{header_row}</tr>
      {snap_rows}
    </table>'''

    rec_box = f'''<div class="rec-box">
      <div style="margin-bottom:10px">{_rec_badge(rec)}</div>
      <table style="font-size:13px;width:auto">
        <tr><td style="padding:3px 12px 3px 0;color:#666">Entry zone</td><td><b>{a.get("entry_zone","N/A")}</b></td></tr>
        <tr><td style="padding:3px 12px 3px 0;color:#666">Stop loss</td><td><b>{a.get("stop_loss","N/A")}</b></td></tr>
        <tr><td style="padding:3px 12px 3px 0;color:#666">Target 1</td><td><b>{a.get("target_1","N/A")}</b></td></tr>
        <tr><td style="padding:3px 12px 3px 0;color:#666">Target 2</td><td><b>{a.get("target_2","N/A")}</b></td></tr>
        <tr><td style="padding:3px 12px 3px 0;color:#666">Risk / Reward</td><td><b>{a.get("risk_reward","N/A")}</b></td></tr>
      </table>
    </div>'''

    analysis_html = _format_analysis_text(a.get("full_analysis", ""))

    return f'''<div class="panel" style="margin-bottom:20px">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px">
    <div>
      <h3 style="font-size:20px;margin-bottom:4px">{symbol} — Deep Analysis</h3>
      <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
        {_direction_badge(direction)}
        <span style="font-size:13px;color:#555">Trend: <b>{trend}</b></span>
        <span style="font-size:13px;color:#555">Scanner Score: <b>{score}/100</b></span>
      </div>
    </div>
    <div style="text-align:right">
      <div style="font-size:12px;color:#888;margin-bottom:4px">Confidence</div>
      {_confidence_bar(conf)}
      {f'<div style="font-size:11px;color:#aaa;margin-top:4px;max-width:260px">{a.get("confidence_reason","")}</div>' if a.get("confidence_reason") else ""}
    </div>
  </div>

  {snap_table}
  {rec_box}

  <details>
    <summary>Read Full AI Analysis</summary>
    <div style="border-top:1px solid #eee;padding-top:14px;line-height:1.6;font-size:13px;color:#444">
      {analysis_html}
    </div>
  </details>
</div>'''


def render_portfolio(portfolio: dict, account: dict) -> str:
    pnl      = portfolio.get("total_unrealized_pnl", 0)
    float_pct= portfolio.get("float_pct", 0)
    risk     = portfolio.get("total_risk_exposure_usd", 0)
    riskp    = portfolio.get("total_risk_pct", 0)
    swap     = portfolio.get("total_swap", 0)
    bias     = portfolio.get("exposure_bias", "NEUTRAL")
    tvol     = portfolio.get("total_volume", 0)
    lvol     = portfolio.get("long_volume", 0)
    svol     = portfolio.get("short_volume", 0)
    pnl_color= "#00b894" if pnl >= 0 else "#d63031"
    swap_color= "#d63031" if swap < 0 else "#00b894"

    cards = "".join([
        _card("Open Positions",  str(portfolio.get("position_count", 0))),
        _card("Unrealized P/L",  f'${pnl:+,.2f}', f'{float_pct:+.2f}% of balance', color=pnl_color),
        _card("Total Volume",    f'{tvol} lots',   f'L: {lvol} | S: {svol}'),
        _card("Risk Exposure",   f'${risk:,.2f}',  f'{riskp:.1f}% of balance',
              color="#d63031" if riskp > 5 else "#fdcb6e" if riskp > 2 else "#00b894"),
        _card("Swap / Rollover", f'${swap:+.2f}',  color=swap_color),
        _card("Exposure Bias",   bias.split()[0],  " ".join(bias.split()[1:]),
              color="#00b894" if "LONG" in bias else "#d63031" if "SHORT" in bias else "#636e72"),
    ])

    positions = portfolio.get("positions", [])
    pos_rows  = ""
    if positions:
        for p in positions:
            bg    = _pnl_color(p["profit"])
            dur   = f"{p['duration_h']:.1f}h"
            pnlc  = '#00b894' if p['profit'] >= 0 else '#d63031'
            cur   = p.get("current", p["open_price"])
            move  = round(cur - p["open_price"], 2) if p["type"] == "BUY" else round(p["open_price"] - cur, 2)
            move_c= "#00b894" if move >= 0 else "#d63031"
            pos_rows += f'''<tr style="background:{bg}">
              <td>{p["ticket"]}</td>
              <td><b>{p["symbol"]}</b></td>
              <td>{"↑ BUY" if p["type"]=="BUY" else "↓ SELL"}</td>
              <td><b>{p["volume"]}</b></td>
              <td>{p["open_price"]}</td>
              <td>{cur}</td>
              <td style="color:{move_c};font-weight:600">{move:+.2f}</td>
              <td>{p["sl"] or "—"}</td>
              <td>{p["tp"] or "—"}</td>
              <td style="color:{pnlc};font-weight:600">${p["profit"]:+.2f}</td>
              <td>${p["swap"]:+.2f}</td>
              <td>{p["risk_pct"]}%</td>
              <td>{dur}</td>
            </tr>'''
        pos_table = f'''<table>
          <tr>
            <th>Ticket</th><th>Symbol</th><th>Dir</th><th>Volume</th>
            <th>Entry</th><th>Current</th><th>Move</th>
            <th>SL</th><th>TP</th><th>P/L</th>
            <th>Swap</th><th>Risk%</th><th>Duration</th>
          </tr>
          {pos_rows}
        </table>'''
    else:
        pos_table = '<p style="color:#888;font-style:italic;padding:12px 0">No open positions.</p>'

    suggestions = portfolio.get("suggestions", [])
    sug_html = ""
    if suggestions:
        items = "".join(f"<li>{s}</li>" for s in suggestions)
        sug_html = f'<div class="suggestion-box"><b>Risk Alerts</b><ul style="margin-top:8px;padding-left:20px">{items}</ul></div>'

    return f'''
{_section_title("Portfolio — Open Positions")}
<div class="panel">
  <div class="cards-row">{cards}</div>
  {pos_table}
  {sug_html}
</div>'''


def render_history(history: dict) -> str:
    if history["total_trades"] == 0:
        return f'''
{_section_title("Trade History (90 Days)")}
<div class="panel"><p style="color:#888;font-style:italic">No closed trades in the last 90 days.</p></div>'''

    wrc    = "#00b894" if history["win_rate"] >= 55 else "#d63031"
    pfc    = "#00b894" if history["profit_factor"] >= 1 else "#d63031"
    pnlc   = "#00b894" if history["total_profit"] >= 0 else "#d63031"
    expc   = "#00b894" if history["expectancy"] >= 0 else "#d63031"

    cards = "".join([
        _card("Total Trades",  str(history["total_trades"])),
        _card("Wins",          str(history["wins"]),    color="#00b894"),
        _card("Losses",        str(history["losses"]),  color="#d63031"),
        _card("Win Rate",      f'{history["win_rate"]}%', color=wrc),
        _card("Total P/L",     f'${history["total_profit"]:+,.2f}', color=pnlc),
        _card("Profit Factor", str(history["profit_factor"]), color=pfc),
        _card("Avg Win",       f'${history["avg_win"]:.2f}', color="#00b894"),
        _card("Avg Loss",      f'${history["avg_loss"]:.2f}', color="#d63031"),
        _card("Expectancy",    f'${history["expectancy"]:.2f}', color=expc),
    ])

    # Best / worst trade highlight
    best  = history.get("best_trade")
    worst = history.get("worst_trade")
    highlights = ""
    if best:
        bt = best
        highlights += f'''<div style="background:#c8f7c5;border-radius:6px;padding:12px 16px;flex:1;min-width:200px">
          <b>Best Trade</b><br>
          {bt.get("symbol","—")} {bt.get("direction","—")} &nbsp;|&nbsp;
          <span style="color:#00b894;font-weight:700">${bt["profit"]:+.2f}</span><br>
          <span style="font-size:12px;color:#555">{str(bt.get("close_time",""))[:10]}</span>
        </div>'''
    if worst:
        wt = worst
        highlights += f'''<div style="background:#f7c5c5;border-radius:6px;padding:12px 16px;flex:1;min-width:200px">
          <b>Worst Trade</b><br>
          {wt.get("symbol","—")} {wt.get("direction","—")} &nbsp;|&nbsp;
          <span style="color:#d63031;font-weight:700">${wt["profit"]:+.2f}</span><br>
          <span style="font-size:12px;color:#555">{str(wt.get("close_time",""))[:10]}</span>
        </div>'''
    highlights_html = f'<div style="display:flex;gap:12px;flex-wrap:wrap;margin:16px 0">{highlights}</div>'

    # Per-symbol table
    sym_rows = ""
    for s in history["by_symbol"]:
        wr_c = "#00b894" if s["win_rate"] >= 55 else "#d63031"
        pl_c = "#00b894" if s["total_profit"] >= 0 else "#d63031"
        sym_rows += f'''<tr>
          <td><b>{s["symbol"]}</b></td><td>{s["trades"]}</td><td>{s["wins"]}</td>
          <td style="color:{wr_c};font-weight:600">{s["win_rate"]}%</td>
          <td style="color:{pl_c};font-weight:600">${s["total_profit"]:+.2f}</td>
        </tr>'''

    sym_table = f'''<table style="margin-top:16px">
      <tr><th>Symbol</th><th>Trades</th><th>Wins</th><th>Win Rate</th><th>Total P/L</th></tr>
      {sym_rows}
    </table>'''

    # Patterns
    patterns = history.get("patterns", [])
    pat_html = ""
    if patterns:
        items = "".join(f"<li>{p}</li>" for p in patterns)
        pat_html = f'<div class="pattern-box"><b>Insights & Patterns</b><ul style="margin-top:8px;padding-left:20px">{items}</ul></div>'

    # Recent 50 trades table with pagination
    trades    = history.get("trades", [])
    trade_rows= ""
    for t in trades:
        bg  = _pnl_color(t["profit"])
        plc = "#00b894" if t["profit"] >= 0 else "#d63031"
        ot  = str(t.get("open_time",""))[:16]
        ct  = str(t.get("close_time",""))[:16]
        trade_rows += f'''<tr style="background:{bg}">
          <td>{ot}</td><td>{ct}</td>
          <td><b>{t.get("symbol","—")}</b></td>
          <td>{"↑ BUY" if t.get("direction")=="BUY" else "↓ SELL"}</td>
          <td>{t.get("open_price","—")}</td><td>{t.get("close_price","—")}</td>
          <td>{t.get("volume","—")}</td>
          <td style="color:{plc};font-weight:600">${t["profit"]:+.2f}</td>
        </tr>'''

    recent_trends_note = f'Recent 10 trades win rate: <b style="color:{wrc}">{history["recent_10_win_rate"]}%</b> vs overall <b>{history["win_rate"]}%</b> — <b>{history["performance_trend"]}</b>'

    return f'''
{_section_title(f'Trade History (Last 90 Days) — {history["total_trades"]} Trades')}
<div class="panel">
  <div class="cards-row">{cards}</div>
  {highlights_html}
  <p style="font-size:13px;color:#555;margin:8px 0">{recent_trends_note}</p>
  {pat_html}
  {sym_table}

  <details style="margin-top:20px">
    <summary>Recent 50 Trades Detail</summary>
    <table style="margin-top:12px">
      <tr><th>Open</th><th>Close</th><th>Symbol</th><th>Dir</th>
          <th>Entry</th><th>Exit</th><th>Vol</th><th>P/L</th></tr>
      {trade_rows}
    </table>
  </details>
</div>'''


# ── main builder ─────────────────────────────────────────────────────────────

def build_report(account: dict,
                 scanner_results: list,
                 analyses: list,
                 portfolio: dict,
                 history: dict) -> str:

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    analysis_cards = ""
    for i, a in enumerate(analyses):
        analysis_cards += render_analysis_card(a, i)

    deep_section = ""
    if analyses:
        count = len(analyses)
        deep_section = f'''
{_section_title(f"Deep Analysis — Top {count} Opportunity Symbol{'s' if count>1 else ''}")}
{analysis_cards}'''

    body = (
        render_scanner(scanner_results)
        + deep_section
        + render_portfolio(portfolio, account)
        + render_history(history)
    )

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta http-equiv="refresh" content="120">
  <title>AI Market Analysis Report</title>
  <style>{CSS}</style>
</head>
<body>
{render_header(account, now)}
<div class="wrap">
{body}
<p style="text-align:center;color:#bbb;font-size:12px;margin-top:30px">
  AI Market Analysis Bot &nbsp;|&nbsp; Powered by MetaTrader5 + Claude claude-opus-4-6 &nbsp;|&nbsp;
  {now} &nbsp;|&nbsp; <i>For informational use only. Not financial advice.</i>
</p>
</div>
</body>
</html>'''
