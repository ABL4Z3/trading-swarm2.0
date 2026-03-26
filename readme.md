# Trading Swarm 2.0 (Railway Ready)

Production-oriented crypto trading bot built around the FALCON v1 strategy, with risk controls, structured trade logging, and optional Telegram alerts.

## What This Repo Includes

- `trading_bot.py`: Main live bot loop (Binance futures testnet/live via config)
- `falcon_strategy.py`: FALCON v1 signal logic
- `position_manager.py`: Position lifecycle + exit management (SL/TP/EMA reversal)
- `trade_logger.py`: SQLite trade/event logging
- `alerts.py`: Telegram notifications (optional)
- `config.py`: Environment-driven runtime config
- `Procfile`, `railway.json`, `runtime.txt`: Railway deployment config

## Strategy Snapshot

FALCON v1 uses multi-layer confluence:

1. EMA200 trend filter
2. EMA 8/21 crossover timing
3. MACD momentum confirmation
4. RSI range filter
5. Volume spike confirmation

Exit/risk logic is handled with:

- ATR-based stop loss and take profit
- EMA reversal early-exit checks
- Circuit-breaker style limits from env config

## Requirements Files

This project uses **two separate requirements files**:

- **`requirements.txt`** - Full development dependencies including ML libraries, backtesting tools, and experimental features. Use this for local development and testing.
  
- **`requirements-railway.txt`** - Minimal production dependencies (~150MB) for Railway deployment. Removes heavy ML/CUDA packages to prevent build timeouts (reduces from 3-4GB to ~150MB, build time from 5+ min to <1 min).

The trading bot gracefully handles missing optional packages (RL risk model, news sentiment) and works perfectly with the minimal Railway requirements.

## Quick Start (Local)

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
# source .venv/bin/activate

pip install -r requirements.txt
python trading_bot.py
```

## Environment Variables

Create a local `.env` file (do not commit it) and set at least:

```env
TRADING_MODE=testnet

BINANCE_TESTNET_API_KEY=...
BINANCE_TESTNET_SECRET=...

# Only for live mode
BINANCE_LIVE_API_KEY=
BINANCE_LIVE_SECRET=

MAX_DAILY_LOSS_PCT=5.0
MAX_DRAWDOWN_PCT=20.0
MAX_CONSECUTIVE_LOSSES=5
DEFAULT_RISK_PER_TRADE=0.01
ENABLE_CIRCUIT_BREAKERS=true
VOLATILITY_BRAKE_MULTIPLIER=2.0

# Optional
CRYPTOPANIC_API_KEY=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

## Deploy on Railway

**⚠️ Important: Railway Geo-Restriction**

Railway servers may be in a region where Binance blocks access (HTTP 451 error). If deployment fails with "Service unavailable from a restricted location", see **`GEO_RESTRICTION_FIX.md`** for solutions:
- Use a proxy service (free or paid)
- Switch to a different exchange (Bybit, OKX)
- Deploy to a different platform (Heroku, DigitalOcean)

**Deployment Steps:**

1. Push this repo to GitHub.
2. In Railway, create a new project from the GitHub repo.
3. Railway automatically uses:
   - `Procfile`: `worker: python trading_bot.py`
   - `runtime.txt`: Python 3.11
   - `railway.json`: Build config (uses `requirements-railway.txt`)
4. Add all required env vars in Railway Variables (see Environment Variables section).
5. **(Optional) Add proxy if needed**: `HTTPS_PROXY=http://user:pass@proxy:port`
6. Deploy and monitor logs in Railway dashboard.

**Note**: Railway uses the minimal `requirements-railway.txt` file to keep build times fast (<1 min) and prevent timeouts. The bot includes all necessary trading functionality with these minimal dependencies.

Detailed deploy notes: see `RAILWAY_DEPLOY.md` and `GEO_RESTRICTION_FIX.md`

## Safety Notes

- Start with `TRADING_MODE=testnet`.
- Validate behavior for at least 1-2 weeks before live trading.
- Begin live mode with small risk and capital.
- Never commit `.env` or API credentials.

## Disclaimer

This software is for educational and research purposes. Trading involves risk and can result in loss of capital. Past backtest results do not guarantee future performance.
