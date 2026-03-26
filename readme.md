# Trading Swarm 2.0 (Railway Ready)

Production-oriented crypto trading bot built around the FALCON v1 strategy, with risk controls, structured trade logging, and optional Telegram alerts.

## ⚠️ IMPORTANT: Binance Demo Mode Required

**As of March 2024**, Binance deprecated their futures testnet sandbox mode. This bot now uses:
- **Binance Futures Testnet** (demo trading API)
- Free virtual funds for paper trading
- See **`BINANCE_DEMO_SETUP.md`** for step-by-step API key setup

## What This Repo Includes

- `trading_bot.py`: Main live bot loop (Binance futures demo/live via config)
- `falcon_strategy.py`: FALCON v1 signal logic
- `position_manager.py`: Position lifecycle + exit management (SL/TP/EMA reversal)
- `trade_logger.py`: SQLite trade/event logging
- `alerts.py`: Telegram notifications (optional)
- `config.py`: Environment-driven runtime config
- `Procfile`, `railway.json`, `nixpacks.toml`, `runtime.txt`: Railway deployment config
- `BINANCE_DEMO_SETUP.md`: Complete guide to get testnet API keys

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

# Get these from https://testnet.binancefuture.com/
# See BINANCE_DEMO_SETUP.md for detailed instructions
BINANCE_TESTNET_API_KEY=your_demo_api_key_here
BINANCE_TESTNET_SECRET=your_demo_secret_here

# Only for live mode
BINANCE_LIVE_API_KEY=
BINANCE_LIVE_SECRET=

MAX_DAILY_LOSS_PCT=5.0
MAX_DRAWDOWN_PCT=20.0
MAX_CONSECUTIVE_LOSSES=5
DEFAULT_RISK_PER_TRADE=0.01
ENABLE_CIRCUIT_BREAKERS=true
VOLATILITY_BRAKE_MULTIPLIER=2.0

# Proxy (required for Railway deployment to bypass geo-restrictions)
HTTPS_PROXY=http://your_proxy_here

# Optional
CRYPTOPANIC_API_KEY=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

## Deploy on Railway

**⚠️ IMPORTANT: Get Binance Demo API Keys First**

Before deploying, you **must** get Binance Futures Testnet API keys:
1. Visit: https://testnet.binancefuture.com/
2. Create account / Sign in
3. Generate API keys (enable Futures trading)
4. See **`BINANCE_DEMO_SETUP.md`** for detailed step-by-step guide

**⚠️ Important: Railway Geo-Restriction**

Railway servers may be in a region where Binance blocks access (HTTP 451 error). Solution: Use a proxy service.
- See **`WORKING_PROXIES.md`** for tested working proxies
- See **`GEO_RESTRICTION_FIX.md`** for alternative solutions

**Deployment Steps:**

1. **Get Binance demo API keys** (see BINANCE_DEMO_SETUP.md)
2. Push this repo to GitHub
3. In Railway, create a new project from the GitHub repo
4. Railway automatically uses:
   - `nixpacks.toml`: Build configuration
   - `runtime.txt`: Python 3.11
   - `Procfile`: Worker command
5. **Add environment variables in Railway** (Variables tab):
   ```
   TRADING_MODE=testnet
   BINANCE_TESTNET_API_KEY=your_key_from_testnet_binancefuture_com
   BINANCE_TESTNET_SECRET=your_secret_from_testnet_binancefuture_com
   HTTPS_PROXY=http://upewvaya:cutbmu4o8skt@142.111.67.146:5611/
   MAX_DAILY_LOSS_PCT=5.0
   MAX_DRAWDOWN_PCT=20.0
   MAX_CONSECUTIVE_LOSSES=5
   DEFAULT_RISK_PER_TRADE=0.01
   ENABLE_CIRCUIT_BREAKERS=true
   ```
6. Save and wait for deployment (~1 minute)
7. Check logs for "Connection successful"

**Note**: Railway uses the minimal `requirements-railway.txt` file to keep build times fast (<1 min) and prevent timeouts.

**Detailed Guides:**
- `BINANCE_DEMO_SETUP.md` - Get testnet API keys (START HERE!)
- `WORKING_PROXIES.md` - Working proxy configurations
- `RAILWAY_DEPLOY.md` - Full deployment guide
- `GEO_RESTRICTION_FIX.md` - Troubleshooting geo-restrictions

## Safety Notes

- Start with `TRADING_MODE=testnet`.
- Validate behavior for at least 1-2 weeks before live trading.
- Begin live mode with small risk and capital.
- Never commit `.env` or API credentials.

## Disclaimer

This software is for educational and research purposes. Trading involves risk and can result in loss of capital. Past backtest results do not guarantee future performance.
