"""
alerts.py - Telegram Alert System
═══════════════════════════════════════════════════════════
Sends real-time alerts to Telegram for trades, errors, and
daily summaries.

SETUP:
1. Create bot at https://t.me/BotFather
2. Get your chat ID at https://t.me/userinfobot
3. Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to .env
═══════════════════════════════════════════════════════════
"""

import requests
import logging
from datetime import datetime
from typing import Optional
from config import get_config

log = logging.getLogger(__name__)


class TelegramAlerter:
    """
    Sends alerts to Telegram for trade notifications and errors.
    Falls back to console logging if Telegram is not configured.
    """

    def __init__(self):
        self.config = get_config()
        self.bot_token = self.config.telegram_bot_token
        self.chat_id = self.config.telegram_chat_id
        self.enabled = bool(self.bot_token and self.chat_id)

        if self.enabled:
            log.info("Telegram alerts enabled")
        else:
            log.info("Telegram alerts disabled (credentials not set)")

    def _send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """Send a message via Telegram API."""
        if not self.enabled:
            log.info(f"[ALERT] {text}")
            return False

        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode,
            }
            response = requests.post(url, data=data, timeout=10)

            if response.status_code == 200:
                return True
            else:
                log.error(f"Telegram API error: {response.text}")
                return False

        except Exception as e:
            log.error(f"Failed to send Telegram message: {e}")
            return False

    def trade_entry(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        quantity: float,
        stop_loss: float,
        take_profit: float,
        strategy: str = "FALCON",
    ):
        """Alert when a trade is opened."""
        pnl_risk = (entry_price - stop_loss) * quantity
        pnl_target = (take_profit - entry_price) * quantity

        message = f"""
<b>🎯 NEW TRADE ENTRY</b>

<b>Symbol:</b> {symbol}
<b>Side:</b> {side.upper()}
<b>Entry:</b> ${entry_price:,.2f}
<b>Size:</b> {quantity:.6f}

<b>Stop Loss:</b> ${stop_loss:,.2f} (-${abs(pnl_risk):.2f})
<b>Take Profit:</b> ${take_profit:,.2f} (+${pnl_target:.2f})

<b>Strategy:</b> {strategy}
<b>Time:</b> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
        self._send_message(message.strip())

    def trade_exit(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        exit_price: float,
        pnl_usd: float,
        pnl_pct: float,
        exit_reason: str,
    ):
        """Alert when a trade is closed."""
        emoji = "🟢" if pnl_usd >= 0 else "🔴"
        sign = "+" if pnl_usd >= 0 else ""

        message = f"""
<b>{emoji} TRADE CLOSED</b>

<b>Symbol:</b> {symbol}
<b>Exit Reason:</b> {exit_reason}

<b>Entry:</b> ${entry_price:,.2f}
<b>Exit:</b> ${exit_price:,.2f}

<b>P&L:</b> {sign}${pnl_usd:.2f} ({sign}{pnl_pct:.2f}%)

<b>Time:</b> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
        self._send_message(message.strip())

    def circuit_breaker(self, reason: str):
        """Alert when circuit breaker activates."""
        message = f"""
<b>⚠️ CIRCUIT BREAKER ACTIVATED</b>

<b>Reason:</b> {reason}

Trading has been paused to prevent further losses.

<b>Time:</b> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
        self._send_message(message.strip())

    def daily_summary(self, stats: dict, balance: float):
        """Send daily trading summary."""
        emoji = "🟢" if stats.get("total_pnl", 0) >= 0 else "🔴"
        sign = "+" if stats.get("total_pnl", 0) >= 0 else ""

        message = f"""
<b>📊 DAILY TRADING SUMMARY</b>

<b>Date:</b> {datetime.now().strftime("%Y-%m-%d")}

<b>Current Balance:</b> ${balance:,.2f}
<b>Daily P&L:</b> {sign}${stats.get("total_pnl", 0):.2f}

<b>Trades Today:</b> {stats.get("total_trades", 0)}
<b>Win Rate:</b> {stats.get("win_rate", 0):.1f}%
<b>Profit Factor:</b> {stats.get("profit_factor", 0):.2f}

<b>Largest Win:</b> ${stats.get("largest_win", 0):.2f}
<b>Largest Loss:</b> ${stats.get("largest_loss", 0):.2f}

{emoji}
"""
        self._send_message(message.strip())

    def error(self, error_type: str, message: str):
        """Alert on system errors."""
        msg = f"""
<b>❌ SYSTEM ERROR</b>

<b>Type:</b> {error_type}
<b>Message:</b> {message}

<b>Time:</b> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
        self._send_message(msg.strip())

    def startup(self, mode: str, balance: float):
        """Alert on system startup."""
        message = f"""
<b>🚀 TRADING BOT STARTED</b>

<b>Mode:</b> {"TESTNET" if mode == "testnet" else "⚠️ LIVE TRADING"}
<b>Balance:</b> ${balance:,.2f}

Bot is now monitoring for trading opportunities.

<b>Time:</b> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
        self._send_message(message.strip())

    def custom(self, title: str, body: str, emoji: str = "ℹ️"):
        """Send a custom alert."""
        message = f"""
<b>{emoji} {title}</b>

{body}

<b>Time:</b> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
        self._send_message(message.strip())


# Global alerter instance
_alerter: Optional[TelegramAlerter] = None


def get_alerter() -> TelegramAlerter:
    """Get or create the global alerter instance."""
    global _alerter
    if _alerter is None:
        _alerter = TelegramAlerter()
    return _alerter


if __name__ == "__main__":
    # Test the alerter
    alerter = get_alerter()

    print("Testing alerts...")
    print(f"Telegram enabled: {alerter.enabled}")

    # Test startup alert
    alerter.startup("testnet", 1000.0)

    # Test trade entry
    alerter.trade_entry(
        symbol="BTC/USDT",
        side="long",
        entry_price=50000.0,
        quantity=0.01,
        stop_loss=49500.0,
        take_profit=51000.0,
    )

    # Test trade exit
    alerter.trade_exit(
        symbol="BTC/USDT",
        side="long",
        entry_price=50000.0,
        exit_price=51000.0,
        pnl_usd=10.0,
        pnl_pct=2.0,
        exit_reason="TAKE_PROFIT",
    )

    print("Alerts sent (check Telegram or console)")
