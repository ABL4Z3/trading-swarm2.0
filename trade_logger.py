"""
trade_logger.py - Trade Logging & Database Persistence
═══════════════════════════════════════════════════════════
Logs all trades to SQLite database and provides reporting.
═══════════════════════════════════════════════════════════
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

log = logging.getLogger(__name__)

DB_FILE = "trades.db"


class TradeLogger:
    """
    Persistent trade logging to SQLite database.
    Provides trade history, statistics, and reporting.
    """

    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Trades table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                quantity REAL NOT NULL,
                stop_loss REAL,
                take_profit REAL,
                pnl_usd REAL,
                pnl_pct REAL,
                exit_reason TEXT,
                entry_time TEXT NOT NULL,
                exit_time TEXT,
                strategy TEXT,
                order_id TEXT,
                metadata TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Daily stats table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                starting_balance REAL,
                ending_balance REAL,
                total_pnl REAL,
                total_trades INTEGER,
                winning_trades INTEGER,
                losing_trades INTEGER,
                largest_win REAL,
                largest_loss REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Events table (for monitoring/debugging)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                message TEXT,
                data TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()
        log.info(f"Trade database initialized: {self.db_path}")

    def log_trade(self, trade: dict) -> int:
        """
        Log a completed trade to the database.
        Returns the trade ID.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO trades (
                symbol, side, entry_price, exit_price, quantity,
                stop_loss, take_profit, pnl_usd, pnl_pct, exit_reason,
                entry_time, exit_time, strategy, order_id, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                trade.get("symbol"),
                trade.get("side"),
                trade.get("entry_price"),
                trade.get("exit_price"),
                trade.get("quantity"),
                trade.get("stop_loss"),
                trade.get("take_profit"),
                trade.get("pnl_usd"),
                trade.get("pnl_pct"),
                trade.get("exit_reason"),
                trade.get("entry_time"),
                trade.get("exit_time"),
                trade.get("strategy"),
                trade.get("order_id"),
                json.dumps(trade.get("metadata", {})),
            ),
        )

        trade_id = cursor.lastrowid
        conn.commit()
        conn.close()

        log.info(f"Trade logged to database: ID={trade_id}")
        return trade_id

    def log_entry(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        quantity: float,
        stop_loss: float,
        take_profit: float,
        strategy: str = "FALCON",
    ) -> int:
        """Log a trade entry (before it's closed)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO trades (
                symbol, side, entry_price, quantity, stop_loss, 
                take_profit, entry_time, strategy
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                symbol,
                side,
                entry_price,
                quantity,
                stop_loss,
                take_profit,
                datetime.now().isoformat(),
                strategy,
            ),
        )

        trade_id = cursor.lastrowid
        conn.commit()
        conn.close()

        log.info(f"Trade entry logged: ID={trade_id}")
        return trade_id

    def update_trade_exit(
        self,
        trade_id: int,
        exit_price: float,
        pnl_usd: float,
        pnl_pct: float,
        exit_reason: str,
    ) -> bool:
        """Update a trade with exit information."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE trades SET
                exit_price = ?,
                pnl_usd = ?,
                pnl_pct = ?,
                exit_reason = ?,
                exit_time = ?
            WHERE id = ?
        """,
            (
                exit_price,
                pnl_usd,
                pnl_pct,
                exit_reason,
                datetime.now().isoformat(),
                trade_id,
            ),
        )

        conn.commit()
        conn.close()
        return cursor.rowcount > 0

    def log_event(self, event_type: str, message: str, data: dict = None):
        """Log a system event."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO events (event_type, message, data)
            VALUES (?, ?, ?)
        """,
            (event_type, message, json.dumps(data or {})),
        )

        conn.commit()
        conn.close()

    def get_trades(self, days: int = 7, symbol: str = None) -> List[dict]:
        """Get recent trades."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        since = (datetime.now() - timedelta(days=days)).isoformat()

        if symbol:
            cursor.execute(
                """
                SELECT * FROM trades 
                WHERE entry_time >= ? AND symbol = ?
                ORDER BY entry_time DESC
            """,
                (since, symbol),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM trades 
                WHERE entry_time >= ?
                ORDER BY entry_time DESC
            """,
                (since,),
            )

        trades = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return trades

    def get_stats(self, days: int = 30) -> dict:
        """Get trading statistics for the past N days."""
        trades = self.get_trades(days=days)

        if not trades:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0,
                "total_pnl": 0,
                "avg_win": 0,
                "avg_loss": 0,
                "profit_factor": 0,
                "largest_win": 0,
                "largest_loss": 0,
            }

        # Filter only closed trades
        closed = [t for t in trades if t.get("exit_price")]

        if not closed:
            return {"total_trades": 0}

        winners = [t for t in closed if (t.get("pnl_usd") or 0) > 0]
        losers = [t for t in closed if (t.get("pnl_usd") or 0) <= 0]

        total_pnl = sum(t.get("pnl_usd", 0) or 0 for t in closed)
        gross_profit = sum(t.get("pnl_usd", 0) or 0 for t in winners)
        gross_loss = abs(sum(t.get("pnl_usd", 0) or 0 for t in losers))

        return {
            "total_trades": len(closed),
            "winning_trades": len(winners),
            "losing_trades": len(losers),
            "win_rate": len(winners) / len(closed) * 100 if closed else 0,
            "total_pnl": round(total_pnl, 2),
            "avg_win": round(gross_profit / len(winners), 2) if winners else 0,
            "avg_loss": round(gross_loss / len(losers), 2) if losers else 0,
            "profit_factor": round(gross_profit / gross_loss, 2)
            if gross_loss > 0
            else float("inf"),
            "largest_win": max((t.get("pnl_usd", 0) or 0 for t in winners), default=0),
            "largest_loss": min((t.get("pnl_usd", 0) or 0 for t in losers), default=0),
        }

    def update_daily_stats(self, starting_balance: float, ending_balance: float):
        """Update daily statistics."""
        today = datetime.now().strftime("%Y-%m-%d")
        trades = self.get_trades(days=1)
        closed = [t for t in trades if t.get("exit_price")]
        winners = [t for t in closed if (t.get("pnl_usd") or 0) > 0]
        losers = [t for t in closed if (t.get("pnl_usd") or 0) <= 0]

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO daily_stats (
                date, starting_balance, ending_balance, total_pnl,
                total_trades, winning_trades, losing_trades,
                largest_win, largest_loss
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                today,
                starting_balance,
                ending_balance,
                ending_balance - starting_balance,
                len(closed),
                len(winners),
                len(losers),
                max((t.get("pnl_usd", 0) or 0 for t in winners), default=0),
                min((t.get("pnl_usd", 0) or 0 for t in losers), default=0),
            ),
        )

        conn.commit()
        conn.close()

    def print_summary(self, days: int = 7):
        """Print a summary of recent trading activity."""
        stats = self.get_stats(days)

        print("=" * 50)
        print(f"  TRADING SUMMARY (Last {days} Days)")
        print("=" * 50)
        print(f"  Total Trades:    {stats['total_trades']}")
        print(f"  Winners/Losers:  {stats['winning_trades']}/{stats['losing_trades']}")
        print(f"  Win Rate:        {stats['win_rate']:.1f}%")
        print(f"  Total P&L:       ${stats['total_pnl']:+.2f}")
        print(f"  Profit Factor:   {stats['profit_factor']:.2f}")
        print(f"  Avg Win:         ${stats['avg_win']:.2f}")
        print(f"  Avg Loss:        ${stats['avg_loss']:.2f}")
        print(f"  Largest Win:     ${stats['largest_win']:.2f}")
        print(f"  Largest Loss:    ${stats['largest_loss']:.2f}")
        print("=" * 50)


# Global logger instance
_logger: Optional[TradeLogger] = None


def get_trade_logger() -> TradeLogger:
    """Get or create the global trade logger instance."""
    global _logger
    if _logger is None:
        _logger = TradeLogger()
    return _logger


if __name__ == "__main__":
    # Test the logger
    logger = get_trade_logger()

    # Log a test trade
    test_trade = {
        "symbol": "BTC/USDT",
        "side": "long",
        "entry_price": 50000.0,
        "exit_price": 51000.0,
        "quantity": 0.01,
        "stop_loss": 49500.0,
        "take_profit": 52000.0,
        "pnl_usd": 10.0,
        "pnl_pct": 2.0,
        "exit_reason": "TAKE_PROFIT",
        "entry_time": datetime.now().isoformat(),
        "exit_time": datetime.now().isoformat(),
        "strategy": "FALCON",
    }

    logger.log_trade(test_trade)
    logger.print_summary()
