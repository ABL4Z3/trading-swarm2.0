# BINANCE DEMO TRADING MODE SETUP GUIDE

## 🎯 IMPORTANT UPDATE (March 2024)

Binance **deprecated their futures testnet sandbox mode**. The new approach is:
- Use **Binance Futures Testnet** (demo trading)
- Same interface, paper trading only (no real money)
- Free virtual funds for testing

---

## 📋 STEP-BY-STEP: Get Binance Demo API Keys

### Step 1: Create Binance Futures Testnet Account

**1. Visit Binance Futures Testnet:**
   - Go to: https://testnet.binancefuture.com/

**2. Sign Up / Log In:**
   - If you don't have an account, click "Register"
   - You can use your regular Binance account email OR create a new test account
   - No verification needed for testnet

**3. Get Free Test Funds:**
   - After login, your testnet account will have free USDT for testing
   - Usually starts with 1,000 - 100,000 test USDT (virtual money)

---

### Step 2: Generate API Keys

**1. Navigate to API Management:**
   - Click your profile icon (top right)
   - Select **"API Management"** from dropdown

**2. Create New API Key:**
   - Click **"Create API"** button
   - Enter a label (e.g., "TradingBot" or "FALCON")
   - Click **"Create"**

**3. Copy Your Credentials:**
   - **API Key**: Long string starting with uppercase letters
   - **Secret Key**: Another long string (shown only once!)
   - ⚠️ **IMPORTANT**: Save both immediately - Secret is shown only once!

**4. Enable Futures Trading:**
   - After creating the key, you'll see it in the API list
   - Click **"Edit"** next to your key
   - Make sure **"Enable Futures"** is checked ✅
   - Click **"Save"**

**5. Configure IP Restrictions (Optional but Recommended):**
   - Option A: **Unrestricted** (easiest for Railway/cloud deployment)
   - Option B: **Whitelist Railway IPs** (more secure but harder to set up)
   - For testing: Use "Unrestricted"

---

### Step 3: Update Railway Environment Variables

**1. Go to Railway Dashboard:**
   - https://railway.app/dashboard
   - Click your `trading-swarm2.0` project
   - Click **"Variables"** tab

**2. Update/Add These Variables:**

**Replace or add:**
```
BINANCE_TESTNET_API_KEY = <your_new_testnet_api_key>
BINANCE_TESTNET_SECRET = <your_new_testnet_secret>
```

**Keep these the same:**
```
TRADING_MODE = testnet
HTTPS_PROXY = http://upewvaya:cutbmu4o8skt@142.111.67.146:5611/
MAX_DAILY_LOSS_PCT = 5.0
MAX_DRAWDOWN_PCT = 20.0
MAX_CONSECUTIVE_LOSSES = 5
DEFAULT_RISK_PER_TRADE = 0.01
ENABLE_CIRCUIT_BREAKERS = true
```

**3. Save:**
   - Railway will auto-redeploy with new keys
   - Wait ~1 minute for deployment

---

## 🧪 STEP 4: Verify Bot Connection

**Check Railway Logs for:**

✅ **SUCCESS:**
```
[INFO] [Exchange] Using HTTPS proxy: http://upewvaya:...
[INFO] [Exchange] Setting up DEMO trading mode for futures...
[INFO] [Exchange] Demo mode configured with testnet URLs
[INFO] [Exchange] Using: https://testnet.binancefuture.com
[INFO] [Exchange] Connection successful
[INFO] [Exchange] Account balance retrieved: X assets
[INFO] Trading Bot Started (FALCON v1 - Testnet Mode)
```

❌ **FAILURE (Bad API Keys):**
```
[ERROR] [Exchange] Failed to initialize: binance {"code":-2015,"msg":"Invalid API-key, IP, or permissions for action."}
```
→ Double-check your API key and secret, make sure Futures is enabled

❌ **FAILURE (Geo-restriction):**
```
[ERROR] 451 Service unavailable from a restricted location
```
→ Make sure HTTPS_PROXY variable is set (it should already be there)

---

## 📊 TESTNET FEATURES

**What You Get:**
- ✅ Free virtual USDT for testing (usually 10,000 - 100,000)
- ✅ Real-time market data (same as live Binance)
- ✅ All order types supported (market, limit, stop-loss, take-profit)
- ✅ Same trading rules as live futures
- ✅ No risk - completely paper trading

**Limitations:**
- ⚠️ Virtual profits don't transfer to live account
- ⚠️ Testnet funds reset periodically (every few months)
- ⚠️ Lower liquidity than live market (might see wider spreads)
- ⚠️ Execution might be slightly different from live

---

## 🔐 SECURITY BEST PRACTICES

**For Testnet (Demo) Keys:**
- ✅ Enable Futures trading only (disable spot, margin)
- ✅ Set IP restrictions if possible (or use unrestricted for Railway)
- ✅ Never commit API keys to GitHub (use Railway variables)
- ✅ Can use unrestricted access (it's just testnet)

**When You Go Live Later:**
- 🔒 **MUST** enable IP whitelist
- 🔒 **MUST** disable withdrawals
- 🔒 **NEVER** share or commit live keys
- 🔒 Start with tiny position sizes (0.1% risk per trade)

---

## 🆘 TROUBLESHOOTING

### Issue 1: "Invalid API key" Error
**Solution:**
- Verify you copied the full API key (no spaces)
- Verify you copied the full secret key
- Check that "Enable Futures" is checked in API settings
- Regenerate keys if needed

### Issue 2: "Timestamp" Error
**Solution:**
- Railway servers have correct time, this shouldn't happen
- If it does, it means API key permissions issue
- Regenerate API keys with Futures enabled

### Issue 3: Still Getting 451 Geo-Restriction
**Solution:**
- Make sure HTTPS_PROXY variable is set in Railway
- Try switching to UK proxy if Japan proxy fails:
  ```
  HTTPS_PROXY = http://upewvaya:cutbmu4o8skt@31.59.20.176:6754/
  ```

### Issue 4: Bot Connects but No Trades
**Solution:**
- FALCON v1 is highly selective (~0-2 signals per day)
- Check logs for "Analyzing market..." messages
- Strategy waits for perfect confluence of 5 indicators
- Be patient - quality over quantity!

---

## 📱 MONITORING YOUR BOT

**Railway Logs:**
- Go to Railway Dashboard → Your Project → "Logs" tab
- Should see market analysis every 15 minutes
- Trade signals will show entry/exit details

**Binance Testnet Dashboard:**
- Visit: https://testnet.binancefuture.com/
- View open positions, order history, balance
- All trades from your bot will appear here

**Expected Behavior:**
- Market check every 15 minutes (timeframe setting)
- Very few signals (0-2 per day average)
- When signal triggers: Entry → SL/TP set → Position monitoring
- Exit when: TP hit, SL hit, or EMA reversal detected

---

## 🎓 UNDERSTANDING DEMO VS LIVE

| Feature | Testnet (Demo) | Live Trading |
|---------|----------------|--------------|
| Money | Virtual (fake) | Real money |
| Market Data | Real-time | Real-time |
| Order Execution | Simulated | Real |
| Risk | Zero | Actual loss possible |
| Liquidity | Lower | Higher |
| Slippage | Similar | Can be worse |
| Recommended Duration | 1-4 weeks | After validation |

**Recommendation**: Run on testnet for **at least 1-2 weeks** to validate:
- Bot runs 24/7 without crashes
- Signals trigger correctly
- Risk management works (SL/TP)
- Circuit breakers activate when needed
- Performance matches expectations

---

## ✅ QUICK CHECKLIST

Before moving to live trading, make sure:
- [ ] Bot runs for 7+ days without crashes
- [ ] At least 10+ trades executed successfully
- [ ] Circuit breakers tested (manually trigger loss conditions)
- [ ] Win rate and profit factor acceptable
- [ ] You understand every log message
- [ ] You're comfortable with max drawdown
- [ ] You have a plan for when strategy fails
- [ ] Starting live with <1% of total capital

---

## 🚀 READY TO DEPLOY?

**After getting your testnet API keys:**
1. Add them to Railway variables (BINANCE_TESTNET_API_KEY, BINANCE_TESTNET_SECRET)
2. Keep HTTPS_PROXY as is (Japan proxy)
3. Keep TRADING_MODE=testnet
4. Save and wait for Railway to redeploy (~1 min)
5. Check logs for "Connection successful"
6. Monitor for 1-2 weeks
7. Review performance
8. If good → Switch to live with small capital

---

## 🔗 USEFUL LINKS

- Binance Futures Testnet: https://testnet.binancefuture.com/
- Binance Testnet Guide: https://www.binance.com/en/support/faq/how-to-test-my-functions-on-binance-testnet-ab78f9a1b8824cf0a106b4229c76496d
- CCXT Documentation: https://docs.ccxt.com/#/
- Railway Dashboard: https://railway.app/dashboard

---

**Questions or issues?** Check the logs and error messages - most problems are:
1. Wrong API keys (copy-paste error)
2. Futures not enabled on API key
3. Proxy not configured (geo-restriction)

Good luck with your testing! 🚀
