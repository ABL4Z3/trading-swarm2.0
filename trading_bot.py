"""
trading_bot.py - Robust AI Trading Bot (FALCON v1)
═══════════════════════════════════════════════════════════
COMPLETE REWRITE with all critical fixes:
- Secure API key loading from .env
- FALCON v1 strategy (the +62.5% performer)
- Full exit management (SL, TP, EMA reversal)
- Position monitoring loop
- Circuit breakers
- Telegram alerts
- Trade logging to database
- Proper error handling and recovery

This replaces main_swarm.py with a production-ready system.
═══════════════════════════════════════════════════════════
"""

import time
import ccxt
import pandas as pd
import numpy as np
import sys
import logging
import os
from datetime import datetime, timedelta

# Local imports
from config import get_config, print_config_summary
from falcon_strategy import falcon_signal, should_exit_early
from position_manager import PositionManager, CircuitBreaker, ExitReason
from trade_logger import get_trade_logger
from alerts import get_alerter

# Optional: Risk agent (gracefully handle if not available)
try:
    from stable_baselines3 import PPO

    RISK_MODEL_AVAILABLE = True
except ImportError:
    RISK_MODEL_AVAILABLE = False

# Optional: Sentinel (news sentiment)
try:
    from sentinel_agent import get_crypto_news, analyze_sentiment

    SENTINEL_AVAILABLE = True
except ImportError:
    SENTINEL_AVAILABLE = False


# ==========================================
#        LOGGING SETUP
# ==========================================
def setup_logging():
    """Configure logging with UTF-8 encoding for Windows."""
    log_format = "%(asctime)s [%(levelname)s] %(message)s"

    handlers = [
        logging.FileHandler("trading_bot.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ]

    logging.basicConfig(level=logging.INFO, format=log_format, handlers=handlers)

    # Force Windows Console to handle UTF-8
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except:
            pass

    return logging.getLogger(__name__)


# ==========================================
#        TRADING BOT CLASS
# ==========================================
class TradingBot:
    """
    Production-ready AI Trading Bot using FALCON v1 strategy.

    Features:
    - Multi-agent confluence (Sentinel, Sniper, Risk Boss)
    - Proper exit management (SL/TP/EMA reversal)
    - Circuit breakers for risk management
    - Telegram alerts
    - Database trade logging
    """

    def __init__(self):
        self.log = setup_logging()
        self.log.info("=" * 60)
        self.log.info("  FALCON TRADING BOT - Initializing")
        self.log.info("=" * 60)

        # Load configuration
        self.config = get_config()
        print_config_summary()

        # Initialize exchange
        self.exchange = self._init_exchange()

        # Initialize components
        self.position_manager = PositionManager(self.exchange, max_positions=1)
        self.circuit_breaker = CircuitBreaker(self.config)
        self.trade_logger = get_trade_logger()
        self.alerter = get_alerter()

        # Load risk model if available
        self.risk_model = self._load_risk_model()

        # State
        self.current_bias = "NEUTRAL"
        self.last_news_check = 0
        self.running = False
        self.loop_count = 0

        # ATR tracking for volatility brake
        self.recent_atrs = []
        self.normal_atr = 0

        self.log.info("Bot initialized successfully")

    def _init_exchange(self):
        """Initialize exchange connection with proper configuration."""
        try:
            exchange_config = {
                "apiKey": self.config.binance_api_key,
                "secret": self.config.binance_secret,
                "enableRateLimit": True,
                "options": {"defaultType": "future"},
            }

            # Add proxy settings if configured (for geo-restricted regions)
            if self.config.http_proxy or self.config.https_proxy:
                exchange_config["proxies"] = {}
                if self.config.http_proxy:
                    exchange_config["proxies"]["http"] = self.config.http_proxy
                    self.log.info(
                        f"[Exchange] Using HTTP proxy: {self.config.http_proxy}"
                    )
                if self.config.https_proxy:
                    exchange_config["proxies"]["https"] = self.config.https_proxy
                    self.log.info(
                        f"[Exchange] Using HTTPS proxy: {self.config.https_proxy}"
                    )

            exchange = ccxt.binance(exchange_config)

            # Enable demo/testnet mode if configured
            if self.config.is_testnet:
                # Binance deprecated sandbox mode for futures (March 2024)
                # New approach: Use demo trading mode with manual URL override
                # Demo API endpoint: https://testnet.binancefuture.com

                self.log.info("[Exchange] Setting up DEMO trading mode for futures...")

                # Override URLs to point to demo/testnet endpoints
                exchange.urls["api"] = {
                    "public": "https://testnet.binancefuture.com/fapi/v1",
                    "private": "https://testnet.binancefuture.com/fapi/v1",
                }
                exchange.urls["test"] = {
                    "public": "https://testnet.binancefuture.com/fapi/v1",
                    "private": "https://testnet.binancefuture.com/fapi/v1",
                }

                # Mark as demo/test environment
                exchange.options["test"] = True

                self.log.info("[Exchange] Demo mode configured with testnet URLs")
                self.log.info("[Exchange] Using: https://testnet.binancefuture.com")

            # Test connection
            balance = exchange.fetch_balance()
            self.log.info("[Exchange] Connection successful")
            self.log.info(
                f"[Exchange] Account balance retrieved: {len(balance.get('info', {}))} assets"
            )
            return exchange

        except Exception as e:
            self.log.error(f"[Exchange] Failed to initialize: {e}")
            raise

    def _load_risk_model(self):
        """Load the RL risk model if available."""
        if not RISK_MODEL_AVAILABLE:
            self.log.warning("[Risk Model] stable_baselines3 not available")
            return None

        model_path = "risk_agent_v1.zip"
        if os.path.exists(model_path):
            try:
                model = PPO.load(model_path, device="cpu")
                self.log.info(f"[Risk Model] Loaded from {model_path}")
                return model
            except Exception as e:
                self.log.error(f"[Risk Model] Failed to load: {e}")
                return None
        else:
            self.log.warning(f"[Risk Model] {model_path} not found")
            return None

    # ==========================================
    #        CORE FUNCTIONS
    # ==========================================

    def get_balance(self) -> float:
        """Get available USDT balance."""
        try:
            balance = self.exchange.fetch_balance()
            if "USDT" in balance:
                return float(balance["USDT"]["free"])
            elif "info" in balance and "assets" in balance["info"]:
                for asset in balance["info"]["assets"]:
                    if asset["asset"] == "USDT":
                        return float(asset["availableBalance"])
            return 0.0
        except Exception as e:
            self.log.error(f"[Balance] Error: {e}")
            return 0.0

    def fetch_ohlcv(self, symbol: str, limit: int = 250) -> pd.DataFrame:
        """Fetch OHLCV data from exchange."""
        try:
            candles = self.exchange.fetch_ohlcv(
                symbol, self.config.timeframe, limit=limit
            )
            df = pd.DataFrame(
                candles, columns=["timestamp", "open", "high", "low", "close", "volume"]
            )
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)
            return df.astype(float)
        except Exception as e:
            self.log.error(f"[Data] Fetch error: {e}")
            return pd.DataFrame()

    def update_news_sentiment(self):
        """Update market sentiment from news."""
        if not SENTINEL_AVAILABLE:
            return

        now = time.time()
        if now - self.last_news_check < self.config.news_interval:
            return

        try:
            self.log.info("[Sentinel] Checking news...")
            news = get_crypto_news()

            if news:
                sentiment = analyze_sentiment(news)
                if "BULLISH" in sentiment.upper():
                    self.current_bias = "BULLISH"
                elif "BEARISH" in sentiment.upper():
                    self.current_bias = "BEARISH"
                else:
                    self.current_bias = "NEUTRAL"
                self.log.info(f"[Sentinel] Market bias: {self.current_bias}")
            else:
                self.log.info("[Sentinel] No significant news")

            self.last_news_check = now

        except Exception as e:
            self.log.error(f"[Sentinel] Error: {e}")

    def get_risk_decision(self, df: pd.DataFrame) -> str:
        """Get position sizing decision from Risk Agent."""
        if not self.risk_model:
            return "1.0%"  # Default fallback

        try:
            # Prepare normalized observation
            current = df.iloc[-1]
            prev = df.iloc[-2]
            sma_20 = df["close"].rolling(20).mean().iloc[-1]

            if pd.isna(sma_20):
                sma_20 = current["close"]

            norm_price = current["close"] / sma_20
            norm_vol = np.log(current["volume"] + 1) / 10.0
            norm_mom = (current["close"] - prev["close"]) / prev["close"] * 100
            norm_volat = (current["high"] - current["low"]) / current["close"] * 100

            obs = np.array(
                [norm_price, norm_vol, norm_mom, norm_volat], dtype=np.float32
            )

            action, _ = self.risk_model.predict(obs, deterministic=True)
            risk_map = {0: "SKIP", 1: "0.5%", 2: "1.0%", 3: "2.0%"}
            return risk_map.get(int(action), "SKIP")

        except Exception as e:
            self.log.error(f"[Risk Model] Prediction error: {e}")
            return "1.0%"

    def execute_entry(self, signal, risk_pct: float) -> bool:
        """Execute a trade entry."""
        try:
            balance = self.get_balance()
            if balance < 10:
                self.log.warning("[Entry] Insufficient balance")
                return False

            # Calculate position size based on risk
            risk_amount = balance * risk_pct
            sl_distance = signal.entry_price - signal.stop_loss

            if sl_distance <= 0:
                self.log.warning("[Entry] Invalid SL distance")
                return False

            quantity = risk_amount / sl_distance
            position_usd = quantity * signal.entry_price

            # Safety check
            if position_usd < 10:
                position_usd = 10
                quantity = position_usd / signal.entry_price

            self.log.info(
                f"[Entry] Executing: BUY {quantity:.6f} @ ${signal.entry_price:.2f}"
            )

            # Execute market order
            order = self.exchange.create_order(
                symbol=self.config.symbol, type="market", side="buy", amount=quantity
            )

            # Get fill price
            fill_price = float(order.get("average", signal.entry_price))

            # Recalculate SL/TP based on actual fill
            atr = signal.atr
            adjusted_sl = fill_price - 1.5 * atr
            adjusted_tp = fill_price + 3.0 * atr

            # Register position
            position = self.position_manager.open_position(
                symbol=self.config.symbol,
                side="long",
                entry_price=fill_price,
                quantity=quantity,
                stop_loss=adjusted_sl,
                take_profit=adjusted_tp,
                strategy_name="FALCON_v1",
                risk_percent=risk_pct,
                atr_at_entry=atr,
            )

            # Log to database
            self.trade_logger.log_entry(
                symbol=self.config.symbol,
                side="long",
                entry_price=fill_price,
                quantity=quantity,
                stop_loss=adjusted_sl,
                take_profit=adjusted_tp,
                strategy="FALCON_v1",
            )

            # Send alert
            self.alerter.trade_entry(
                symbol=self.config.symbol,
                side="long",
                entry_price=fill_price,
                quantity=quantity,
                stop_loss=adjusted_sl,
                take_profit=adjusted_tp,
                strategy="FALCON_v1",
            )

            self.log.info(f"[Entry] Order filled @ ${fill_price:.2f}")
            return True

        except Exception as e:
            self.log.error(f"[Entry] Failed: {e}")
            self.alerter.error("Entry Failed", str(e))
            return False

    def check_and_execute_exits(self, df: pd.DataFrame):
        """Check positions and execute exits if needed."""
        if not self.position_manager.has_position(self.config.symbol):
            return

        position = self.position_manager.positions[self.config.symbol]
        current_price = df.iloc[-1]["close"]

        # Check EMA reversal
        ema_reversal = should_exit_early(df, position.entry_price)

        # Check exit conditions
        exit_reason = position.check_exit_conditions(current_price, ema_reversal)

        if exit_reason:
            self.execute_exit(position, current_price, exit_reason)

    def execute_exit(self, position, exit_price: float, reason: ExitReason):
        """Execute a position exit."""
        try:
            self.log.info(
                f"[Exit] Executing: SELL @ ${exit_price:.2f} ({reason.value})"
            )

            # Execute market sell order
            order = self.exchange.create_order(
                symbol=self.config.symbol,
                type="market",
                side="sell",
                amount=position.quantity,
            )

            # Get actual fill price
            fill_price = float(order.get("average", exit_price))

            # Close position and record
            trade = self.position_manager.close_position(
                self.config.symbol, fill_price, reason
            )

            # Log to database
            self.trade_logger.log_trade(trade)

            # Send alert
            self.alerter.trade_exit(
                symbol=self.config.symbol,
                side="long",
                entry_price=position.entry_price,
                exit_price=fill_price,
                pnl_usd=trade["pnl_usd"],
                pnl_pct=trade["pnl_pct"],
                exit_reason=reason.value,
            )

            self.log.info(f"[Exit] Completed: ${trade['pnl_usd']:+.2f}")

        except Exception as e:
            self.log.error(f"[Exit] Failed: {e}")
            self.alerter.error("Exit Failed", str(e))

    def calculate_current_atr(self, df: pd.DataFrame) -> float:
        """Calculate current ATR for volatility tracking."""
        if len(df) < 15:
            return 0

        high = df["high"]
        low = df["low"]
        close = df["close"]

        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(14).mean().iloc[-1]

        return atr if not pd.isna(atr) else 0

    def update_volatility_tracking(self, atr: float):
        """Track ATR for volatility brake."""
        self.recent_atrs.append(atr)
        if len(self.recent_atrs) > 100:
            self.recent_atrs.pop(0)

        if len(self.recent_atrs) >= 20:
            self.normal_atr = np.mean(self.recent_atrs[:20])  # Baseline

    # ==========================================
    #        MAIN TRADING LOOP
    # ==========================================

    def run(self):
        """Main trading loop."""
        self.running = True
        self.log.info("=" * 60)
        self.log.info("  FALCON TRADING BOT - Starting")
        self.log.info("=" * 60)

        # Get initial balance
        balance = self.get_balance()
        self.position_manager.reset_daily_stats(balance)

        # Send startup alert
        mode = "testnet" if self.config.is_testnet else "live"
        self.alerter.startup(mode, balance)

        self.log.info(f"[Bot] Balance: ${balance:.2f}")
        self.log.info(f"[Bot] Mode: {'TESTNET' if self.config.is_testnet else 'LIVE'}")
        self.log.info(f"[Bot] Monitoring {self.config.symbol}...")

        while self.running:
            try:
                self.loop_count += 1

                # Daily reset check
                balance = self.get_balance()
                self.position_manager.reset_daily_stats(balance)

                # 1. Update news sentiment
                self.update_news_sentiment()

                # 2. Fetch market data
                df = self.fetch_ohlcv(self.config.symbol)
                if df.empty or len(df) < 215:
                    self.log.warning("[Bot] Insufficient data")
                    time.sleep(30)
                    continue

                current_price = df.iloc[-1]["close"]
                atr = self.calculate_current_atr(df)
                self.update_volatility_tracking(atr)

                # 3. Check circuit breakers
                should_block, reason = self.circuit_breaker.check(
                    self.position_manager, balance, atr, self.normal_atr
                )

                if should_block:
                    self.alerter.circuit_breaker(reason)
                    self.log.warning(f"[Circuit Breaker] {reason}")
                    time.sleep(300)  # Wait 5 minutes
                    continue

                # 4. Check and execute exits for open positions
                self.check_and_execute_exits(df)

                # 5. Look for new entry signals (if no position)
                if not self.position_manager.has_position(self.config.symbol):
                    signal = falcon_signal(df)

                    if signal:
                        self.log.info(
                            f"[Sniper] Signal detected @ ${signal.entry_price:.2f}"
                        )

                        # Check news filter
                        if self.current_bias == "BEARISH":
                            self.log.info("[Sentinel] Vetoed by BEARISH sentiment")
                        else:
                            # Get risk decision
                            risk_decision = self.get_risk_decision(df)

                            if risk_decision == "SKIP":
                                self.log.info("[Risk Boss] VETOED - Market unsafe")
                            else:
                                risk_pct = float(risk_decision.replace("%", "")) / 100
                                self.log.info(
                                    f"[Confluence] FULL CONFLUENCE! Size: {risk_decision}"
                                )
                                self.execute_entry(signal, risk_pct)

                # 6. Heartbeat log
                pos_status = (
                    "IN POSITION"
                    if self.position_manager.has_position(self.config.symbol)
                    else "No position"
                )
                self.log.debug(
                    f"[Heartbeat] BTC: ${current_price:.2f} | "
                    f"Bias: {self.current_bias} | "
                    f"Bal: ${balance:.2f} | "
                    f"{pos_status}"
                )

                # Print to console
                print(
                    f"[{datetime.now().strftime('%H:%M:%S')}] "
                    f"BTC: ${current_price:.2f} | "
                    f"Bias: {self.current_bias} | "
                    f"Bal: ${balance:.2f} | "
                    f"{pos_status}    ",
                    end="\r",
                )

                # Sleep until next candle (60 seconds)
                time.sleep(60)

            except KeyboardInterrupt:
                self.log.info("[Bot] Shutting down...")
                self.running = False
                break

            except Exception as e:
                self.log.error(f"[Bot] Loop error: {e}")
                self.alerter.error("Loop Error", str(e))
                time.sleep(30)  # Wait before retry

        # Cleanup
        self.log.info("[Bot] Shutdown complete")

        # Print final stats
        stats = self.position_manager.get_stats()
        self.log.info(
            f"[Stats] Trades: {stats['total_trades']} | "
            f"Win Rate: {stats['win_rate']:.1f}% | "
            f"Daily P&L: ${stats['daily_pnl']:.2f}"
        )

    def stop(self):
        """Stop the trading bot."""
        self.running = False


# ==========================================
#        ENTRY POINT
# ==========================================


def main():
    """Main entry point."""
    print("\n" + "=" * 60)
    print("  FALCON TRADING BOT v2.0 - Production Ready")
    print("  Using FALCON v1 Strategy (+62.5% backtest return)")
    print("=" * 60 + "\n")

    try:
        bot = TradingBot()
        bot.run()
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()
