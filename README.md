# AI Market Analysis Bot

Real-time XAUUSD analysis bot powered by MetaTrader5 live data and Claude AI. Generates an HTML report pushed to GitHub Pages every 3 minutes.

---

## How It Connects to MetaTrader5

### Requirements

1. **MetaTrader5 desktop app** must be installed and running on Windows
2. **Python MetaTrader5 package**:
   ```
   pip install MetaTrader5
   ```
3. The MT5 terminal must be **logged in** to your broker account before running the bot

### The Connection

The bot uses the official MetaTrader5 Python integration — it communicates directly with the MT5 terminal running on your machine via a local COM interface. No API keys or broker credentials are needed in the code.

```python
import MetaTrader5 as mt5

# Initialize connection to the running MT5 terminal
mt5.initialize()

# Fetch live OHLCV data (most recent 200 candles, M5 timeframe)
rates = mt5.copy_rates_from_pos("XAUUSD_", mt5.TIMEFRAME_M5, 0, 200)

# Get open positions
positions = mt5.positions_get()

# Get trade history
from datetime import datetime, timedelta
deals = mt5.history_deals_get(datetime.now() - timedelta(days=90), datetime.now())

# Always shut down cleanly
mt5.shutdown()
```

### How `mt5.initialize()` Works

- It finds the MT5 terminal process running on your Windows machine
- Opens a shared memory bridge between Python and the terminal
- No username/password needed — it uses the already-logged-in session
- Must be called before any other MT5 function
- Must be followed by `mt5.shutdown()` when done

### Symbol Names

Symbol names are broker-specific. To find the correct name for your broker:

```python
import MetaTrader5 as mt5
mt5.initialize()
symbols = mt5.symbols_get()
for s in symbols:
    if "XAU" in s.name or "Gold" in s.name.lower():
        print(s.name)
mt5.shutdown()
```

For example:
- Equiti broker → `XAUUSD.sd`
- CFI broker → `XAUUSD_`
- Most brokers → `XAUUSD`

---

## Project Structure

```
market_analysis_bot/
├── main.py                # Entry point — orchestrates the full pipeline
├── config.py              # All settings: symbols, timeframes, paths, API keys
├── mt5_connector.py       # MT5 connect / disconnect / account info
├── data_fetcher.py        # Fetch OHLCV, open positions, trade history
├── indicators.py          # EMA, RSI, MACD, Bollinger Bands, ATR
├── scanner.py             # Scores and ranks symbols by opportunity (0–100)
├── symbol_analyzer.py     # Builds Claude AI prompt + parses JSON response
├── portfolio_analyzer.py  # Analyzes open positions and 90-day trade history
├── report_builder.py      # Renders the full HTML report
├── github_publisher.py    # Auto-commits and pushes report to GitHub Pages
└── output/
    └── market_analysis_report.html
```

---

## Setup

### 1. Install Dependencies

```bash
pip install MetaTrader5 pandas anthropic
```

### 2. Set Your Anthropic API Key

The bot reads the key from the Windows environment variable named `API Key`.

To set it permanently:
1. `Win + R` → `sysdm.cpl`
2. **Advanced** → **Environment Variables**
3. **New** under User Variables:
   - Name: `API Key`
   - Value: `sk-ant-...`

### 3. Configure Symbol and Broker

Edit `config.py`:

```python
SYMBOLS = ["XAUUSD_"]   # Use your broker's exact symbol name
```

### 4. Run

```bash
# Single run
python main.py

# Loop every 3 minutes (default)
python main.py --loop

# Custom interval
python main.py --loop --interval 5
```

---

## Data Flow

```
MT5 Terminal (live)
       │
       ▼
data_fetcher.py     ← fetches OHLCV for M5, M15, H1, H4
       │
       ▼
indicators.py       ← calculates EMA10/50/200, RSI, MACD, BB, ATR
       │
       ├──► scanner.py          → scores symbol 0–100
       │
       └──► symbol_analyzer.py  → builds prompt → calls Claude API
                                → parses JSON response
                                       │
                          portfolio_analyzer.py
                          (open positions + history)
                                       │
                                       ▼
                               report_builder.py
                               (renders HTML)
                                       │
                                       ▼
                              github_publisher.py
                              (git commit + push)
                                       │
                                       ▼
                         GitHub Pages (public URL)
```

---

## Timeframes Used

| Timeframe | Purpose              | Candles Fetched |
|-----------|----------------------|-----------------|
| M5        | Scalp / precise entry | 24 candles      |
| M15       | Entry timing          | 16 candles      |
| H1        | Intermediate trend    | 24 candles      |
| H4        | Structure / major trend | 20 candles   |

---

## Claude AI Integration

The bot sends all four timeframes of indicator data to Claude in a single prompt and asks for a structured JSON response containing:

- Trend analysis per timeframe
- Key support and resistance levels
- Scenario probabilities (Bull / Bear / Neutral)
- Analyst summary
- Trade recommendation (BUY / SELL / WAIT) with entry, SL, TP, R:R

Model used: `claude-opus-4-6`

---

## GitHub Pages Publishing

After each report is generated:
1. The HTML is copied to the local clone of the GitHub repo as `index.html`
2. A `git commit` is made with a timestamp
3. `git push` sends it to GitHub
4. GitHub Pages serves it at: `https://khalilhamzeh91.github.io/Market-Analysis`

The page auto-refreshes in the browser every 2 minutes.

---

## Windows Auto-Start

To run the bot automatically on Windows login:

```cmd
schtasks /create /tn "MarketAnalysisBot" /tr "C:\Users\khali\Documents\market_analysis_bot\run_bot.bat" /sc onlogon /f
```

---

## Common Issues

| Error | Cause | Fix |
|-------|-------|-----|
| `Terminal: Call failed` | Wrong symbol name | Run symbol lookup script above |
| `Could not resolve authentication` | API key not found | Check env variable name matches `API Key` |
| MT5 not connecting | Terminal not running | Open and log in to MT5 first |
| Git push rejected | Remote has new commits | The publisher auto-pulls before pushing |
