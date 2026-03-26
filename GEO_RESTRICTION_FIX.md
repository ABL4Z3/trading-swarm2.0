# Fixing Binance Geo-Restriction Error (HTTP 451)

## Problem
Railway deployment failed with error:
```
binance GET https://testnet.binance.vision/api/v3/exchangeInfo 451
"Service unavailable from a restricted location according to 'b. Eligibility' in https://www.binance.com/en/terms."
```

This happens because **Railway's servers are in a region where Binance blocks access**.

---

## Solution Options

### Option 1: Use Free Proxy Service ⭐ RECOMMENDED

Add these environment variables to Railway:

```bash
HTTP_PROXY=http://proxy-server:port
HTTPS_PROXY=http://proxy-server:port
```

**Free Proxy Services:**
- **WebShare.io**: 10 free proxies, 1GB/month free tier
  - Sign up: https://www.webshare.io/
  - Get your proxy: `http://username:password@proxy.webshare.io:80`
  
- **ProxyScrape**: Free public proxies (less reliable)
  - https://proxyscrape.com/free-proxy-list

**Example Railway Variables:**
```
HTTPS_PROXY=http://youruser:yourpass@proxy.webshare.io:80
```

### Option 2: Use Paid Proxy Service (Most Reliable)

**Recommended Services:**
- **Bright Data** (formerly Luminati): $0.001/GB, datacenter proxies
- **Smartproxy**: $2.5/GB, residential proxies
- **IPRoyal**: $1.75/GB, datacenter proxies

**Setup:**
1. Sign up for service
2. Get proxy credentials
3. Add to Railway variables:
   ```
   HTTPS_PROXY=http://user:pass@proxy-host:port
   ```

### Option 3: Switch to Different Exchange (No Proxy Needed)

Use exchanges without geo-restrictions:

**Bybit (Recommended):**
```python
# In trading_bot.py, replace:
exchange = ccxt.binance(...)
# With:
exchange = ccxt.bybit(...)
```

**Changes needed:**
1. Get Bybit testnet API keys: https://testnet.bybit.com/
2. Update `.env`:
   ```
   BYBIT_TESTNET_API_KEY=your_key
   BYBIT_TESTNET_SECRET=your_secret
   ```
3. Modify `trading_bot.py` to use Bybit

**Other Options:**
- OKX (https://www.okx.com/)
- KuCoin (https://www.kucoin.com/)
- Gate.io (https://www.gate.io/)

### Option 4: Deploy to Different Platform

Platforms with better Binance connectivity:

**Heroku** (US/EU regions):
- Free tier: 550-1000 dyno hours/month
- Better geo-location for Binance
- Similar to Railway deployment

**Render** (US regions):
- Free tier: 750 hours/month
- Good Binance connectivity
- Easy GitHub integration

**DigitalOcean App Platform** (Choose US/EU datacenter):
- $5/month minimum
- More control over region
- Excellent Binance connectivity

**Contabo VPS** ($4/month):
- Full VPS control
- Choose your datacenter location
- Most reliable for crypto trading

### Option 5: Use Binance.US (US Traders Only)

If you're in the US, use Binance.US endpoints:

```python
# In trading_bot.py _init_exchange():
exchange.urls['api'] = 'https://api.binance.us'
```

Get API keys from: https://www.binance.us/

---

## Quick Fix: WebShare Proxy Setup

**1. Sign up for WebShare.io free account:**
   - Go to https://www.webshare.io/
   - Sign up (no credit card needed for free tier)
   - Navigate to "Proxy List"

**2. Copy your proxy URL:**
   - Format: `http://username:password@proxy-address:port`
   - Example: `http://myuser:mypass@proxy.webshare.io:80`

**3. Add to Railway:**
   - Go to Railway Dashboard → Your Project → Variables
   - Add new variable:
     ```
     HTTPS_PROXY = http://username:password@proxy.webshare.io:80
     ```
   - Railway will auto-redeploy

**4. Verify in logs:**
   - Look for: `[Exchange] Using HTTPS proxy: http://...`
   - Should see: `[Exchange] Connection successful`

---

## Testing Proxy Locally

Before deploying, test proxy locally:

**1. Add to your `.env` file:**
```bash
HTTPS_PROXY=http://youruser:yourpass@proxy.webshare.io:80
```

**2. Run bot:**
```bash
python trading_bot.py
```

**3. Check logs:**
```
[INFO] [Exchange] Using HTTPS proxy: http://...
[INFO] [Exchange] Sandbox mode enabled
[INFO] [Exchange] Connection successful
```

---

## Troubleshooting

### Proxy connection fails
- Verify proxy credentials are correct
- Check proxy service status (not blocked/down)
- Try different proxy from your provider's list
- Ensure proxy supports HTTPS (most free proxies don't)

### Bot connects but can't trade
- Some proxies block WebSocket connections (needed for real-time data)
- Use datacenter proxy instead of residential proxy
- Upgrade to paid proxy service

### Still getting 451 error
- Railway might be blocking proxy connections
- Try Option 3 (switch exchange) or Option 4 (different platform)
- Contact Railway support about geo-restrictions

---

## Cost Comparison

| Solution | Cost | Reliability | Setup Time |
|----------|------|-------------|------------|
| Free Proxy (WebShare) | $0 | 3/5 | 5 min |
| Paid Proxy | $5-15/mo | 5/5 | 5 min |
| Switch to Bybit | $0 | 5/5 | 15 min |
| Deploy to Heroku | $0-7/mo | 4/5 | 10 min |
| DigitalOcean VPS | $5/mo | 5/5 | 20 min |

**Recommendation**: Start with **WebShare free proxy** (5 min setup). If unreliable, switch to **Bybit exchange** (no proxy needed).

---

## Updated Code

The bot now automatically detects and uses proxy settings from environment variables:
- `HTTP_PROXY` or `http_proxy` → HTTP requests
- `HTTPS_PROXY` or `https_proxy` → HTTPS requests (Binance uses HTTPS)

No code changes needed - just add the environment variable to Railway!
