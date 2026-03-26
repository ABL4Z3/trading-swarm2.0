"""
falcon_strategy.py  —  FALCON: 5-Layer Confluence Strategy
═══════════════════════════════════════════════════════════
Research basis:
  - MACD + RSI combined raises win rate to 55-77% (QuantifiedStrategies, 2025)
  - ATR-based stops beat fixed stops 66% of the time (KJ Trading, 2025)
  - EMA200 macro filter eliminates most losing trades in bear markets
  - Volume spike (1.5x avg) confirms real institutional participation
  - 5-layer confluence = ~0.5-1% of candles fire → quality over quantity

5 ENTRY LAYERS (all must pass):
  1. EMA200  — price above 200 EMA (macro uptrend only)
  2. EMA8/21 — EMA8 crossed above EMA21 within last 3 candles
  3. MACD    — line above signal AND histogram growing
  4. RSI     — between 45 and 68 (momentum, not overbought)
  5. Volume  — current > 1.5x 20-period average

EXIT LOGIC (ATR-based, dynamic):
  - Stop loss  : entry - 1.5 × ATR(14)   → adapts to volatility
  - Take profit: entry + 3.0 × ATR(14)   → 1:2 risk/reward minimum
  - EMA reversal: exit if EMA8 crosses back below EMA21 (trend ended)

DROP THIS INTO backtester_v3.py or main_swarm.py via:
  from falcon_strategy import falcon_signal, FalconTrade
═══════════════════════════════════════════════════════════
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional


@dataclass
class FalconSignal:
    """Returned when all 5 layers pass. Contains entry + exit levels."""
    entry_price:  float
    stop_loss:    float   # entry - 1.5 × ATR
    take_profit:  float   # entry + 3.0 × ATR
    atr:          float
    rsi:          float
    macd_hist:    float
    ema8:         float
    ema21:        float
    ema200:       float
    risk_reward:  float   # always ~2.0


def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss
    return 100 - (100 / (1 + rs))


def _macd(series: pd.Series):
    ema12  = _ema(series, 12)
    ema26  = _ema(series, 26)
    line   = ema12 - ema26
    signal = _ema(line, 9)
    hist   = line - signal
    return line, signal, hist


def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, prev_close = df['high'], df['low'], df['close'].shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low  - prev_close).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def falcon_signal(df: pd.DataFrame) -> Optional[FalconSignal]:
    """
    Run all 5 layers against a window of OHLCV data.
    Returns FalconSignal if all layers pass, None otherwise.

    df: DataFrame with columns [open, high, low, close, volume]
        Needs at least 210 candles for EMA200 to be reliable.
    """
    MIN_CANDLES = 210
    if len(df) < MIN_CANDLES:
        return None

    close  = df['close']
    volume = df['volume']

    # ── Pre-compute indicators ────────────────────────────────────────
    ema8_s   = _ema(close, 8)
    ema21_s  = _ema(close, 21)
    ema200_s = _ema(close, 200)
    rsi_s    = _rsi(close, 14)
    _, _, hist_s = _macd(close)
    atr_s    = _atr(df, 14)
    vol_ma   = volume.rolling(20).mean()

    # Latest values (index -1 = current live candle, -2 = last closed)
    # We use -2 for signals to avoid look-ahead on the current candle
    i = -2

    ema8   = ema8_s.iloc[i]
    ema21  = ema21_s.iloc[i]
    ema200 = ema200_s.iloc[i]
    rsi    = rsi_s.iloc[i]
    hist   = hist_s.iloc[i]
    hist_prev = hist_s.iloc[i - 1]
    atr    = atr_s.iloc[i]
    vol    = volume.iloc[i]
    vol_avg= vol_ma.iloc[i]
    price  = close.iloc[i]

    # Guard: any NaN means not enough data yet
    if any(np.isnan(v) for v in [ema8, ema21, ema200, rsi, hist, atr, vol_avg]):
        return None

    # ── Layer 1: Macro trend — price above EMA200 ─────────────────────
    if price <= ema200:
        return None

    # ── Layer 2: EMA8 crossed above EMA21 within last 3 candles ───────
    # Check last 3 closed candles for a crossover
    crossed_recently = False
    for k in range(2, 5):   # candles -2, -3, -4
        e8_now  = ema8_s.iloc[-k]
        e8_prev = ema8_s.iloc[-k - 1]
        e21_now  = ema21_s.iloc[-k]
        e21_prev = ema21_s.iloc[-k - 1]
        if e8_prev <= e21_prev and e8_now > e21_now:
            crossed_recently = True
            break
    if not crossed_recently:
        return None

    # ── Layer 3: MACD — line above signal AND histogram growing ───────
    macd_line_s, signal_line_s, _ = _macd(close)
    macd_line = macd_line_s.iloc[i]
    sig_line  = signal_line_s.iloc[i]

    if macd_line <= sig_line:          # MACD not bullish
        return None
    if hist <= hist_prev:              # histogram shrinking = momentum fading
        return None
    if hist <= 0:                      # histogram must be positive
        return None

    # ── Layer 4: RSI between 45 and 68 ───────────────────────────────
    if not (45 < rsi < 68):
        return None

    # ── Layer 5: Volume spike > 1.5x 20-period average ───────────────
    if vol < vol_avg * 1.5:
        return None

    # ── All layers passed → build signal ─────────────────────────────
    stop_loss   = price - 1.5 * atr
    take_profit = price + 3.0 * atr
    risk        = price - stop_loss
    reward      = take_profit - price
    rr          = reward / risk if risk > 0 else 0

    return FalconSignal(
        entry_price  = round(price,  2),
        stop_loss    = round(stop_loss,   2),
        take_profit  = round(take_profit, 2),
        atr          = round(atr,    4),
        rsi          = round(rsi,    2),
        macd_hist    = round(hist,   6),
        ema8         = round(ema8,   2),
        ema21        = round(ema21,  2),
        ema200       = round(ema200, 2),
        risk_reward  = round(rr,     2),
    )


def should_exit_early(df: pd.DataFrame, entry_price: float) -> bool:
    """
    EMA reversal exit: if EMA8 crosses back below EMA21 after entry,
    the trend has reversed — exit early even if SL/TP not hit.
    """
    if len(df) < 25:
        return False
    ema8_s  = _ema(df['close'], 8)
    ema21_s = _ema(df['close'], 21)
    # Most recent candle: is EMA8 now below EMA21?
    return ema8_s.iloc[-2] < ema21_s.iloc[-2]
