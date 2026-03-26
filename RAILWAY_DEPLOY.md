# FALCON Trading Bot - Railway Deployment Guide

## Quick Deploy to Railway (10 Minutes)

Railway makes deployment dead simple with GitHub integration and automatic builds.

---

## Prerequisites

- GitHub account
- Railway account (sign up at https://railway.app)
- Your trading bot code

---

## Step 1: Push Code to GitHub (3 minutes)

### Option A: Create New GitHub Repo

1. Go to https://github.com/new
2. Name: `falcon-trading-bot` (or anything you want)
3. **IMPORTANT**: Set to **PRIVATE** (contains API keys)
4. Don't initialize with README
5. Click "Create repository"

### Option B: Use Git Commands

```bash
cd C:\Users\Lenovo\Desktop\trading

# Initialize git (if not already)
git init

# Add files (excluding sensitive data - already in .gitignore)
git add .

# Commit
git commit -m "Initial commit - FALCON trading bot"

# Add remote (replace with YOUR repo URL)
git remote add origin https://github.com/YOUR_USERNAME/falcon-trading-bot.git

# Push
git push -u origin main
```

**Note**: Your `.gitignore` already protects `.env` from being committed!

---

## Step 2: Deploy to Railway (5 minutes)

### Connect Railway to GitHub

1. Go to https://railway.app
2. Click "Start a New Project"
3. Select "Deploy from GitHub repo"
4. Authorize Railway to access your GitHub
5. Select `falcon-trading-bot` repository
6. Railway will automatically detect Python and start building!

### Configure Environment Variables

While build is running, add your environment variables:

1. Click on your project
2. Go to "Variables" tab
3. Click "Add Variable" and add each one:

```
BINANCE_TESTNET_API_KEY=tZ8xOTZSpeVhJPGqj1SE292l8gSC2E8bqbTjWfho55mBH08r5horifHkN51VzCoE
BINANCE_TESTNET_SECRET=w2Oq0ESyEpIoSp7izYfOLKPT82eYn2fncvwSwPd6sAF6WLZjJy3UcvGz8mpt2p83
CRYPTOPANIC_API_KEY=bfabc911b30415403563f8b084747488bfcf3e99
TRADING_MODE=testnet
MAX_DAILY_LOSS_PCT=5.0
MAX_DRAWDOWN_PCT=20.0
MAX_CONSECUTIVE_LOSSES=5
DEFAULT_RISK_PER_TRADE=0.01
ENABLE_CIRCUIT_BREAKERS=true
VOLATILITY_BRAKE_MULTIPLIER=2.0
```

**Optional (for Telegram alerts):**
```
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

### Trigger Redeploy

After adding variables:
1. Click "Deployments" tab
2. Click "Deploy" button (or push any change to GitHub)
3. Watch the logs

---

## Step 3: Monitor Your Bot (2 minutes)

### View Logs

1. In Railway dashboard, click your service
2. Click "Logs" tab
3. You should see:

```
=========================================
  FALCON Trading Bot v1.0
=========================================
Mode: TESTNET (Safe - Fake Money)
Exchange: Binance Testnet
Symbol: BTC/USDT
Timeframe: 15m
=========================================

[2026-03-25 10:30:15] Starting bot...
[2026-03-25 10:30:16] Connected to Binance Testnet
[2026-03-25 10:30:17] Account balance: $10,000.00 USDT
[2026-03-25 10:30:18] Monitoring for signals...
```

### Check Status

- Green dot = Running ✅
- Red dot = Error ❌ (check logs)

---

## Railway Features You Get

✅ **Auto-restart** - Bot restarts if it crashes
✅ **Auto-redeploy** - Push to GitHub = instant deploy
✅ **Free tier** - $5 credit/month (enough for testing)
✅ **Easy logs** - View in browser
✅ **Metrics** - CPU, memory, network usage

---

## Cost Breakdown

**Railway Pricing:**
- Free tier: $5 credit/month
- Your bot uses: ~$3-8/month (depending on traffic)
- After free tier: Pay as you go

**Estimated Monthly Cost:**
- First month: FREE ($5 credit)
- After: $3-8/month
- Plus trading fees: ~$5/month

**Total: $8-13/month**

**Expected profit**: ~$17/month (on $1000 capital)
**Net profit**: ~$4-9/month ✅

---

## Database Handling

⚠️ **IMPORTANT**: Railway uses ephemeral storage

**Problem**: SQLite database (`trades.db`) resets on every redeploy

**Solutions:**

### Option 1: Use Railway Volume (Recommended)
```bash
# In Railway settings:
1. Click "Volumes" tab
2. Add volume at path: /app/data
3. Update trading_bot.py to save database to /app/data/trades.db
```

### Option 2: Use Postgres (Better for production)
```bash
# In Railway:
1. Click "New" → "Database" → "Postgres"
2. Get connection string from variables
3. Update bot to use Postgres instead of SQLite
```

### Option 3: Cloud Storage
- Use AWS S3, Google Cloud Storage, or Cloudflare R2
- Export trades.db periodically
- More complex, but most reliable

**For now (testnet)**: Ephemeral storage is fine. You're just testing!

---

## Management

### Restart Bot
- Push any change to GitHub, or
- Click "Restart" in Railway dashboard

### Stop Bot
- In Railway: Settings → "Pause Service"

### Update Code
```bash
# On your PC
cd C:\Users\Lenovo\Desktop\trading
# Make changes to files
git add .
git commit -m "Update strategy"
git push
# Railway auto-deploys!
```

### View Database (if using ephemeral storage)
You can't directly access SQLite on Railway. Options:
1. Add database export endpoint
2. Use Postgres instead
3. Download via temporary volume mount

---

## Troubleshooting

### Build Failed
Check logs for missing dependencies:
```bash
# If you see "ModuleNotFoundError"
# Make sure requirements.txt has the package
# Push update to GitHub
```

### Bot Crashes on Start
1. Check Railway logs for errors
2. Verify environment variables are set correctly
3. Test API keys on Binance Testnet: https://testnet.binance.vision/
4. Check if testnet is down

### Connection Timeout
- Railway servers are in US/EU → higher latency to Binance
- This is normal for Railway
- Still works fine, just slightly slower order execution (1-2 seconds)

### Out of Memory
- Basic Railway plan has 512MB RAM
- Your bot should use ~100-200MB
- If crashes: Upgrade to $10/month plan (2GB RAM)

---

## Going Live (After Testing)

1. **Stop testnet deployment**
   ```bash
   # In Railway Variables, change:
   TRADING_MODE=live
   BINANCE_LIVE_API_KEY=your_real_key
   BINANCE_LIVE_SECRET=your_real_secret
   ```

2. **Reduce risk initially**
   ```bash
   DEFAULT_RISK_PER_TRADE=0.005  # 0.5% instead of 1%
   ```

3. **Redeploy**
   - Push to GitHub or click "Restart"

4. **Monitor closely**
   - Check logs every hour first day
   - Verify trades execute correctly
   - Watch balance on Binance

---

## Alternative: Railway CLI (Advanced)

Install Railway CLI for local testing:

```bash
# Install
npm install -g @railway/cli

# Login
railway login

# Link project
railway link

# Run locally with Railway env vars
railway run python trading_bot.py

# View logs
railway logs

# Deploy manually
railway up
```

---

## Comparison: Railway vs DigitalOcean

| Feature | Railway | DigitalOcean VPS |
|---------|---------|------------------|
| Setup time | 10 min ⚡ | 30 min |
| Monthly cost | $5-8 | $6 |
| Latency | Higher (US/EU) | Lower (Singapore) |
| Auto-deploy | Yes ✅ | No |
| Dashboard | Yes ✅ | No |
| Scaling | Automatic | Manual |
| Database | Ephemeral ⚠️ | Persistent ✅ |
| **Best for** | **Testing/Dev** | **Production** |

**Recommendation**: 
- Start with Railway (easy setup, test fast)
- Move to DigitalOcean when going live with real money

---

## Summary

✅ **10-minute deployment**
✅ **$5/month (free tier)**
✅ **Auto-restart on crash**
✅ **GitHub integration**
✅ **Easy monitoring**

⚠️ **Tradeoffs:**
- Ephemeral database (need volume or Postgres)
- Higher latency vs Singapore VPS
- Limited free tier

**Perfect for testing your bot on testnet!** 🚀

---

## Next Steps

1. Push code to GitHub (private repo!)
2. Deploy to Railway
3. Add environment variables
4. Watch logs
5. Let it run on testnet for 1-2 weeks
6. Review performance
7. Switch to live or move to DigitalOcean VPS

---

## Need Help?

**Railway docs**: https://docs.railway.app
**Check logs**: Railway dashboard → Logs tab
**Status**: https://status.railway.app

**Emergency stop**: Railway dashboard → Settings → Pause Service
