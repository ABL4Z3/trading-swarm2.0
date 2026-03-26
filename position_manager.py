"""
position_manager.py - Position & Exit Management
═══════════════════════════════════════════════════════════
Handles all position tracking, stop-loss, take-profit, and
exit management. This was the CRITICAL missing piece.
═══════════════════════════════════════════════════════════
"""

import time
import logging
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from enum import Enum

log = logging.getLogger(__name__)


class ExitReason(Enum):
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"
    EMA_REVERSAL = "EMA_REVERSAL"
    TRAILING_STOP = "TRAILING_STOP"
    CIRCUIT_BREAKER = "CIRCUIT_BREAKER"
    MANUAL = "MANUAL"
    TIMEOUT = "TIMEOUT"


@dataclass
class Position:
    """Represents an open trading position."""

    symbol: str
    side: str  # "long" or "short"
    entry_price: float
    quantity: float
    stop_loss: float
    take_profit: float
    entry_time: datetime = field(default_factory=datetime.now)

    # Tracking
    peak_price: float = 0.0
    lowest_price: float = float("inf")
    trailing_stop: Optional[float] = None

    # Strategy info
    strategy_name: str = "FALCON"
    risk_percent: float = 0.01
    atr_at_entry: float = 0.0

    def __post_init__(self):
        if self.side == "long":
            self.peak_price = self.entry_price
        else:
            self.lowest_price = self.entry_price

    def update_tracking(self, current_price: float):
        """Update peak/low price tracking for trailing stops."""
        if self.side == "long":
            if current_price > self.peak_price:
                self.peak_price = current_price
        else:
            if current_price < self.lowest_price:
                self.lowest_price = current_price

    def calculate_pnl(self, current_price: float) -> tuple:
        """Calculate current P&L in USD and percentage."""
        if self.side == "long":
            pnl_usd = (current_price - self.entry_price) * self.quantity
            pnl_pct = (current_price - self.entry_price) / self.entry_price * 100
        else:
            pnl_usd = (self.entry_price - current_price) * self.quantity
            pnl_pct = (self.entry_price - current_price) / self.entry_price * 100
        return round(pnl_usd, 2), round(pnl_pct, 3)

    def check_exit_conditions(
        self, current_price: float, ema_reversal: bool = False
    ) -> Optional[ExitReason]:
        """
        Check if any exit conditions are met.
        Returns ExitReason if should exit, None otherwise.
        """
        if self.side == "long":
            # Stop Loss hit
            if current_price <= self.stop_loss:
                return ExitReason.STOP_LOSS

            # Take Profit hit
            if current_price >= self.take_profit:
                return ExitReason.TAKE_PROFIT

            # Trailing Stop (if enabled)
            if self.trailing_stop and current_price <= self.trailing_stop:
                return ExitReason.TRAILING_STOP
        else:
            # Short position (future implementation)
            if current_price >= self.stop_loss:
                return ExitReason.STOP_LOSS
            if current_price <= self.take_profit:
                return ExitReason.TAKE_PROFIT

        # EMA Reversal exit
        if ema_reversal:
            return ExitReason.EMA_REVERSAL

        return None

    def update_trailing_stop(self, atr: float, multiplier: float = 1.5):
        """
        Update trailing stop based on current peak price.
        Only moves up (for longs), never down.
        """
        if self.side == "long":
            new_trailing = self.peak_price - (atr * multiplier)
            if self.trailing_stop is None or new_trailing > self.trailing_stop:
                self.trailing_stop = round(new_trailing, 2)

    def to_dict(self) -> dict:
        """Convert position to dictionary for logging/saving."""
        return {
            "symbol": self.symbol,
            "side": self.side,
            "entry_price": self.entry_price,
            "quantity": self.quantity,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "entry_time": self.entry_time.isoformat(),
            "peak_price": self.peak_price,
            "trailing_stop": self.trailing_stop,
            "strategy": self.strategy_name,
            "risk_percent": self.risk_percent,
        }


class PositionManager:
    """
    Manages all open positions and handles exit logic.
    This is the core component for proper trade management.
    """

    def __init__(self, exchange, max_positions: int = 1):
        self.exchange = exchange
        self.max_positions = max_positions
        self.positions: Dict[str, Position] = {}  # symbol -> Position
        self.trade_history: List[dict] = []

        # Circuit breaker state
        self.daily_pnl = 0.0
        self.consecutive_losses = 0
        self.daily_start_balance = 0.0
        self.last_daily_reset = datetime.now().date()

    def has_position(self, symbol: str) -> bool:
        """Check if we have an open position for this symbol."""
        return symbol in self.positions

    def can_open_position(self) -> bool:
        """Check if we can open a new position."""
        return len(self.positions) < self.max_positions

    def open_position(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        quantity: float,
        stop_loss: float,
        take_profit: float,
        **kwargs,
    ) -> Position:
        """
        Record a new open position.
        Call this AFTER the exchange order is filled.
        """
        position = Position(
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            quantity=quantity,
            stop_loss=stop_loss,
            take_profit=take_profit,
            **kwargs,
        )
        self.positions[symbol] = position
        log.info(
            f"Position opened: {symbol} {side} @ ${entry_price:.2f} | "
            f"SL: ${stop_loss:.2f} | TP: ${take_profit:.2f}"
        )
        return position

    def close_position(
        self, symbol: str, exit_price: float, reason: ExitReason
    ) -> dict:
        """
        Close a position and record the trade.
        Returns trade summary dict.
        """
        if symbol not in self.positions:
            log.warning(f"No position found for {symbol}")
            return {}

        position = self.positions[symbol]
        pnl_usd, pnl_pct = position.calculate_pnl(exit_price)

        trade_record = {
            "symbol": symbol,
            "side": position.side,
            "entry_price": position.entry_price,
            "exit_price": exit_price,
            "quantity": position.quantity,
            "stop_loss": position.stop_loss,
            "take_profit": position.take_profit,
            "peak_price": position.peak_price,
            "pnl_usd": pnl_usd,
            "pnl_pct": pnl_pct,
            "exit_reason": reason.value,
            "entry_time": position.entry_time.isoformat(),
            "exit_time": datetime.now().isoformat(),
            "hold_duration_minutes": (datetime.now() - position.entry_time).seconds
            // 60,
            "strategy": position.strategy_name,
        }

        # Update tracking
        self.trade_history.append(trade_record)
        self.daily_pnl += pnl_usd

        if pnl_usd < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

        # Remove position
        del self.positions[symbol]

        # Log the close
        emoji = "+" if pnl_usd >= 0 else ""
        log.info(
            f"Position closed: {symbol} | {reason.value} | "
            f"P&L: {emoji}${pnl_usd:.2f} ({emoji}{pnl_pct:.2f}%)"
        )

        return trade_record

    def check_all_positions(
        self, current_prices: Dict[str, float], ema_reversals: Dict[str, bool] = None
    ) -> List[dict]:
        """
        Check all open positions for exit conditions.
        Returns list of positions that should be closed.
        """
        to_close = []
        ema_reversals = ema_reversals or {}

        for symbol, position in self.positions.items():
            if symbol not in current_prices:
                continue

            current_price = current_prices[symbol]
            position.update_tracking(current_price)

            # Check exit conditions
            ema_rev = ema_reversals.get(symbol, False)
            exit_reason = position.check_exit_conditions(current_price, ema_rev)

            if exit_reason:
                to_close.append(
                    {
                        "symbol": symbol,
                        "position": position,
                        "current_price": current_price,
                        "reason": exit_reason,
                    }
                )

        return to_close

    def execute_exits(self, to_close: List[dict]) -> List[dict]:
        """
        Execute exit orders for positions that need to be closed.
        Returns list of completed trade records.
        """
        completed = []

        for item in to_close:
            symbol = item["symbol"]
            position = item["position"]
            reason = item["reason"]

            try:
                # Execute market sell order
                log.info(f"Executing exit for {symbol}: {reason.value}")

                order = self.exchange.create_order(
                    symbol=symbol,
                    type="market",
                    side="sell" if position.side == "long" else "buy",
                    amount=position.quantity,
                )

                # Get actual fill price
                fill_price = float(order.get("average", item["current_price"]))

                # Record the trade
                trade = self.close_position(symbol, fill_price, reason)
                trade["order_id"] = order.get("id")
                completed.append(trade)

            except Exception as e:
                log.error(f"Failed to exit {symbol}: {e}")

        return completed

    def reset_daily_stats(self, current_balance: float):
        """Reset daily statistics (call at start of each trading day)."""
        today = datetime.now().date()
        if today > self.last_daily_reset:
            self.daily_pnl = 0.0
            self.daily_start_balance = current_balance
            self.last_daily_reset = today
            log.info(f"Daily stats reset. Starting balance: ${current_balance:.2f}")

    def get_stats(self) -> dict:
        """Get current position manager statistics."""
        total_trades = len(self.trade_history)
        winning_trades = [t for t in self.trade_history if t["pnl_usd"] > 0]

        return {
            "open_positions": len(self.positions),
            "total_trades": total_trades,
            "winning_trades": len(winning_trades),
            "win_rate": len(winning_trades) / total_trades * 100
            if total_trades > 0
            else 0,
            "daily_pnl": self.daily_pnl,
            "consecutive_losses": self.consecutive_losses,
        }


class CircuitBreaker:
    """
    Safety system to halt trading when risk limits are exceeded.
    """

    def __init__(self, config):
        self.config = config
        self.is_active = False
        self.reason = ""
        self.activated_at = None

    def check(
        self,
        position_manager: PositionManager,
        current_balance: float,
        atr: float = 0,
        normal_atr: float = 0,
    ) -> tuple:
        """
        Check all circuit breaker conditions.
        Returns (should_block, reason) tuple.
        """
        if not self.config.enable_circuit_breakers:
            return False, ""

        pm = position_manager

        # Check daily loss limit
        if pm.daily_start_balance > 0:
            daily_loss_pct = abs(pm.daily_pnl) / pm.daily_start_balance * 100
            if pm.daily_pnl < 0 and daily_loss_pct >= self.config.max_daily_loss_pct:
                return self._activate(f"Daily loss limit hit: -{daily_loss_pct:.1f}%")

        # Check max drawdown
        if pm.daily_start_balance > 0:
            drawdown = (
                (pm.daily_start_balance - current_balance)
                / pm.daily_start_balance
                * 100
            )
            if drawdown >= self.config.max_drawdown_pct:
                return self._activate(f"Max drawdown hit: -{drawdown:.1f}%")

        # Check consecutive losses
        if pm.consecutive_losses >= self.config.max_consecutive_losses:
            return self._activate(f"Max consecutive losses: {pm.consecutive_losses}")

        # Check volatility spike
        if atr > 0 and normal_atr > 0:
            vol_ratio = atr / normal_atr
            if vol_ratio >= self.config.volatility_brake_multiplier:
                return self._activate(f"Volatility spike: {vol_ratio:.1f}x normal")

        # All clear
        self.is_active = False
        return False, ""

    def _activate(self, reason: str) -> tuple:
        """Activate the circuit breaker."""
        self.is_active = True
        self.reason = reason
        self.activated_at = datetime.now()
        log.warning(f"CIRCUIT BREAKER ACTIVATED: {reason}")
        return True, reason

    def reset(self):
        """Manually reset the circuit breaker."""
        self.is_active = False
        self.reason = ""
        self.activated_at = None
        log.info("Circuit breaker reset")
