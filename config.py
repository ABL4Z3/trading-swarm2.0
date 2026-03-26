"""
config.py - Centralized Configuration Management
═══════════════════════════════════════════════════════════
Loads all settings from .env file and provides safe defaults.
Import this module instead of hardcoding API keys.
═══════════════════════════════════════════════════════════
"""

import os
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import Optional

# Load environment variables from .env file
load_dotenv()


@dataclass
class TradingConfig:
    """Trading configuration loaded from environment."""

    # Exchange API Keys
    binance_api_key: str
    binance_secret: str
    is_testnet: bool

    # News API
    cryptopanic_api_key: str

    # Telegram Alerts
    telegram_bot_token: Optional[str]
    telegram_chat_id: Optional[str]

    # Risk Management
    max_daily_loss_pct: float
    max_drawdown_pct: float
    max_consecutive_losses: int
    default_risk_per_trade: float

    # Circuit Breakers
    enable_circuit_breakers: bool
    volatility_brake_multiplier: float

    # Trading Settings
    symbol: str = "BTC/USDT"
    timeframe: str = "15m"
    news_interval: int = 3600  # seconds


def load_config() -> TradingConfig:
    """
    Load configuration from environment variables.
    Returns TradingConfig with appropriate API keys based on trading mode.
    """
    trading_mode = os.getenv("TRADING_MODE", "testnet").lower()
    is_testnet = trading_mode != "live"

    # Select appropriate API keys based on mode
    if is_testnet:
        api_key = os.getenv("BINANCE_TESTNET_API_KEY", "")
        secret = os.getenv("BINANCE_TESTNET_SECRET", "")
    else:
        api_key = os.getenv("BINANCE_LIVE_API_KEY", "")
        secret = os.getenv("BINANCE_LIVE_SECRET", "")

        # Safety check: prevent live trading without keys
        if not api_key or not secret:
            raise ValueError(
                "LIVE trading mode selected but BINANCE_LIVE_API_KEY "
                "or BINANCE_LIVE_SECRET not set in .env file!"
            )

    return TradingConfig(
        # Exchange
        binance_api_key=api_key,
        binance_secret=secret,
        is_testnet=is_testnet,
        # News
        cryptopanic_api_key=os.getenv("CRYPTOPANIC_API_KEY", ""),
        # Telegram
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN") or None,
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID") or None,
        # Risk Management
        max_daily_loss_pct=float(os.getenv("MAX_DAILY_LOSS_PCT", "5.0")),
        max_drawdown_pct=float(os.getenv("MAX_DRAWDOWN_PCT", "20.0")),
        max_consecutive_losses=int(os.getenv("MAX_CONSECUTIVE_LOSSES", "5")),
        default_risk_per_trade=float(os.getenv("DEFAULT_RISK_PER_TRADE", "0.01")),
        # Circuit Breakers
        enable_circuit_breakers=os.getenv("ENABLE_CIRCUIT_BREAKERS", "true").lower()
        == "true",
        volatility_brake_multiplier=float(
            os.getenv("VOLATILITY_BRAKE_MULTIPLIER", "2.0")
        ),
    )


# Global config instance (lazy loaded)
_config: Optional[TradingConfig] = None


def get_config() -> TradingConfig:
    """Get or create the global configuration instance."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def print_config_summary():
    """Print a safe summary of current configuration (no secrets)."""
    cfg = get_config()
    print("=" * 50)
    print("  TRADING BOT CONFIGURATION")
    print("=" * 50)
    print(f"  Mode: {'TESTNET' if cfg.is_testnet else '*** LIVE TRADING ***'}")
    print(f"  Symbol: {cfg.symbol}")
    print(f"  Timeframe: {cfg.timeframe}")
    print(
        f"  API Key: {cfg.binance_api_key[:8]}...{cfg.binance_api_key[-4:]}"
        if cfg.binance_api_key
        else "  API Key: NOT SET"
    )
    print(f"  Telegram Alerts: {'Enabled' if cfg.telegram_bot_token else 'Disabled'}")
    print("-" * 50)
    print(f"  Max Daily Loss: {cfg.max_daily_loss_pct}%")
    print(f"  Max Drawdown: {cfg.max_drawdown_pct}%")
    print(f"  Max Consecutive Losses: {cfg.max_consecutive_losses}")
    print(f"  Default Risk/Trade: {cfg.default_risk_per_trade * 100}%")
    print(f"  Circuit Breakers: {'ON' if cfg.enable_circuit_breakers else 'OFF'}")
    print("=" * 50)


if __name__ == "__main__":
    print_config_summary()
