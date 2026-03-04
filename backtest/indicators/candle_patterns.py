"""
Candlestick Pattern Detection for SMC Strategy Confirmation.

Detects hammer, inverted hammer, and engulfing patterns used as
confirmation signals when price reaches an Order Block zone.
"""

import numpy as np
import pandas as pd


def detect_candle_patterns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect confirmation candlestick patterns.

    Patterns detected:
      - Bullish Hammer:   small body at top, long lower wick >= 2× body
      - Bearish Inverted Hammer (Shooting Star): small body at bottom, long upper wick >= 2× body
      - Bullish Engulfing: current bullish candle body engulfs previous bearish candle body
      - Bearish Engulfing: current bearish candle body engulfs previous bullish candle body

    Adds columns:
      `bull_hammer`     – True when bullish hammer detected
      `bear_inv_hammer` – True when bearish inverted hammer detected
      `bull_engulfing`  – True when bullish engulfing detected
      `bear_engulfing`  – True when bearish engulfing detected
      `bull_confirm`    – True when ANY bullish confirmation is present
      `bear_confirm`    – True when ANY bearish confirmation is present
    """
    opens = df['open'].values
    highs = df['high'].values
    lows = df['low'].values
    closes = df['close'].values
    n = len(df)

    bull_hammer = np.zeros(n, dtype=bool)
    bear_inv_hammer = np.zeros(n, dtype=bool)
    bull_engulfing = np.zeros(n, dtype=bool)
    bear_engulfing = np.zeros(n, dtype=bool)

    for i in range(1, n):
        body = abs(closes[i] - opens[i])
        upper_wick = highs[i] - max(closes[i], opens[i])
        lower_wick = min(closes[i], opens[i]) - lows[i]
        candle_range = highs[i] - lows[i]

        # Avoid division by zero
        if candle_range == 0:
            continue

        body_ratio = body / candle_range
        is_bullish = closes[i] > opens[i]
        is_bearish = closes[i] < opens[i]

        # ── Bullish Hammer ──
        # Small body (< 35% of range), long lower wick (>= 2× body), at/near top
        if (body_ratio < 0.35
                and lower_wick >= 2 * body
                and upper_wick < body
                and body > 0):
            bull_hammer[i] = True

        # ── Bearish Inverted Hammer (Shooting Star) ──
        # Small body (< 35% of range), long upper wick (>= 2× body), at/near bottom
        if (body_ratio < 0.35
                and upper_wick >= 2 * body
                and lower_wick < body
                and body > 0):
            bear_inv_hammer[i] = True

        # ── Bullish Engulfing ──
        # Previous candle is bearish, current is bullish
        # Current body fully engulfs previous body
        prev_body_top = max(opens[i - 1], closes[i - 1])
        prev_body_bottom = min(opens[i - 1], closes[i - 1])
        curr_body_top = max(opens[i], closes[i])
        curr_body_bottom = min(opens[i], closes[i])

        prev_is_bearish = closes[i - 1] < opens[i - 1]

        if (is_bullish and prev_is_bearish
                and curr_body_top > prev_body_top
                and curr_body_bottom < prev_body_bottom):
            bull_engulfing[i] = True

        # ── Bearish Engulfing ──
        prev_is_bullish = closes[i - 1] > opens[i - 1]

        if (is_bearish and prev_is_bullish
                and curr_body_top > prev_body_top
                and curr_body_bottom < prev_body_bottom):
            bear_engulfing[i] = True

    df = df.copy()
    df['bull_hammer'] = bull_hammer
    df['bear_inv_hammer'] = bear_inv_hammer
    df['bull_engulfing'] = bull_engulfing
    df['bear_engulfing'] = bear_engulfing

    # Combined confirmation signals
    df['bull_confirm'] = df['bull_hammer'] | df['bull_engulfing']
    df['bear_confirm'] = df['bear_inv_hammer'] | df['bear_engulfing']

    return df
