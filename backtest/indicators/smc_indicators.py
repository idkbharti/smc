"""
SMC Indicators — port of stable.pine logic to pandas.

Translates the Pine Script swing detection, trend (BOS/CHoCH), strong/weak zones,
and valid order-block (liquidity sweep + FVG) logic into column-based pandas operations.

Reference: /home/dev/Desktop/smc/pine/stable.pine
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ─── Constants ────────────────────────────────────────────────────────────────
BULLISH = 1
BEARISH = -1
NEUTRAL = 0


# ─── Data Structures ─────────────────────────────────────────────────────────

@dataclass
class Pivot:
    """Mirrors Pine `type pivot`."""
    current_level: float = float('nan')
    last_level: float = float('nan')
    crossed: bool = False
    bar_time: int = 0
    bar_index: int = 0


@dataclass
class TrailingExtremes:
    """Mirrors Pine `type trailingExtremes`."""
    top: float = float('nan')
    bottom: float = float('nan')
    last_top_idx: int = 0
    last_bottom_idx: int = 0


@dataclass
class ActiveOB:
    """A single order block tracked until mitigation."""
    ob_high: float
    ob_low: float
    bar_index: int        # bar index where OB candle sits
    bias: int             # BULLISH or BEARISH
    partial: bool = False # touched but not fully broken


# ─── 1. Swing Detection ──────────────────────────────────────────────────────

def detect_swings(df: pd.DataFrame, size: int = 50) -> pd.DataFrame:
    """
    Port of Pine `leg()` function.

    For each bar *i*, checks the bar at *i - size*:
      - Bearish leg (found High): high[i-size] > max(high[i-size+1 .. i])
      - Bullish leg (found Low):  low[i-size]  < min(low[i-size+1 .. i])

    Adds columns:
      `swing_leg`  – current leg direction (1 = bullish, 0 = bearish)
      `is_pivot`   – True when the leg direction changes
      `pivot_type` – 'high' | 'low' | NaN
      `pivot_level`– price of the detected pivot
    """
    highs = df['high'].values
    lows = df['low'].values
    n = len(df)

    leg_arr = np.full(n, -1, dtype=int)  # -1 = uninitialised
    prev_leg = -1

    for i in range(n):
        if i < size:
            leg_arr[i] = prev_leg
            continue

        check_idx = i - size
        # Window: bars from (check_idx+1) to i inclusive
        window_high_max = np.max(highs[check_idx + 1: i + 1])
        window_low_min = np.min(lows[check_idx + 1: i + 1])

        if highs[check_idx] > window_high_max:
            prev_leg = 0  # bearish leg  (found a high pivot)
        elif lows[check_idx] < window_low_min:
            prev_leg = 1  # bullish leg  (found a low pivot)

        leg_arr[i] = prev_leg

    df = df.copy()
    df['swing_leg'] = leg_arr

    # Detect changes
    df['is_pivot'] = df['swing_leg'] != df['swing_leg'].shift(1)
    # On the very first valid bar it is not really a "change"
    df.loc[df.index[0], 'is_pivot'] = False

    # Pivot type: when leg switches to 1 (bullish) we found a LOW;
    #             when leg switches to 0 (bearish) we found a HIGH.
    df['pivot_type'] = np.where(
        df['is_pivot'],
        np.where(df['swing_leg'] == 1, 'low', 'high'),
        None
    )

    # Pivot is actually at bar [i - size]
    pivot_level = np.full(n, np.nan)
    for i in range(size, n):
        if df['is_pivot'].iat[i]:
            check_idx = i - size
            if df['pivot_type'].iat[i] == 'low':
                pivot_level[i] = lows[check_idx]
            else:
                pivot_level[i] = highs[check_idx]
    df['pivot_level'] = pivot_level

    return df


# ─── 2. Trend Detection (BOS / CHoCH) ────────────────────────────────────────

def detect_trend(df: pd.DataFrame, size: int = 50) -> pd.DataFrame:
    """
    Port of Pine `getCurrentStructure()` + `displayStructure()` logic.

    Walks bar-by-bar, maintaining swing_high / swing_low pivots and detecting
    BOS (Break of Structure) and CHoCH (Change of Character) events.

    Adds columns:
      `trend`        – running trend: BULLISH(1), BEARISH(-1), NEUTRAL(0)
      `structure`    – 'BOS' | 'CHoCH' | NaN  (on the bar where the break happens)
      `swing_high_level` – current swing high level
      `swing_low_level`  – current swing low level
    """
    highs = df['high'].values
    lows = df['low'].values
    closes = df['close'].values
    n = len(df)

    # Output arrays
    trend_arr = np.zeros(n, dtype=int)
    structure_arr = np.full(n, None, dtype=object)
    sh_level = np.full(n, np.nan)
    sl_level = np.full(n, np.nan)

    # State
    swing_high = Pivot()
    swing_low = Pivot()
    trailing = TrailingExtremes()
    bias = NEUTRAL
    prev_leg = -1

    for i in range(n):
        # ── leg detection ──
        if i >= size:
            check_idx = i - size
            window_high_max = np.max(highs[check_idx + 1: i + 1])
            window_low_min = np.min(lows[check_idx + 1: i + 1])

            if highs[check_idx] > window_high_max:
                new_leg = 0
            elif lows[check_idx] < window_low_min:
                new_leg = 1
            else:
                new_leg = prev_leg

            # ── new pivot ──
            if new_leg != prev_leg and prev_leg != -1:
                if new_leg == 1:  # found a LOW
                    swing_low.last_level = swing_low.current_level
                    swing_low.current_level = lows[check_idx]
                    swing_low.crossed = False
                    swing_low.bar_index = check_idx

                    trailing.bottom = swing_low.current_level
                    trailing.last_bottom_idx = check_idx
                else:  # found a HIGH
                    swing_high.last_level = swing_high.current_level
                    swing_high.current_level = highs[check_idx]
                    swing_high.crossed = False
                    swing_high.bar_index = check_idx

                    trailing.top = swing_high.current_level
                    trailing.last_top_idx = check_idx

                # Initialise trend on first pivot pair
                if bias == NEUTRAL:
                    bias = BULLISH if new_leg == 1 else BEARISH

            prev_leg = new_leg

        # ── update trailing extremes ──
        if not np.isnan(trailing.top):
            if highs[i] > trailing.top:
                trailing.top = highs[i]
                trailing.last_top_idx = i
        if not np.isnan(trailing.bottom):
            if lows[i] < trailing.bottom:
                trailing.bottom = lows[i]
                trailing.last_bottom_idx = i

        # ── BOS / CHoCH checks ──
        # Bullish break
        if (not np.isnan(swing_high.current_level)
                and closes[i] > swing_high.current_level
                and not swing_high.crossed):
            tag = 'CHoCH' if bias == BEARISH else 'BOS'
            bias = BULLISH
            swing_high.crossed = True
            structure_arr[i] = tag

        # Bearish break
        if (not np.isnan(swing_low.current_level)
                and closes[i] < swing_low.current_level
                and not swing_low.crossed):
            tag = 'CHoCH' if bias == BULLISH else 'BOS'
            bias = BEARISH
            swing_low.crossed = True
            structure_arr[i] = tag

        trend_arr[i] = bias
        sh_level[i] = swing_high.current_level
        sl_level[i] = swing_low.current_level

    df = df.copy()
    df['trend'] = trend_arr
    df['structure'] = structure_arr
    df['swing_high_level'] = sh_level
    df['swing_low_level'] = sl_level

    return df


# ─── 3. Strong / Weak Zones ──────────────────────────────────────────────────

def detect_zones(df: pd.DataFrame) -> pd.DataFrame:
    """
    Port of Pine strong/weak high/low logic.

    In BEARISH trend: high = Strong High (hard to break), low = Weak Low
    In BULLISH trend: low = Strong Low (hard to break), high = Weak High

    Requires columns: `trend`, `swing_high_level`, `swing_low_level`

    Adds columns:
      `zone_top`    – trailing extreme top (strongest high-side level)
      `zone_bottom` – trailing extreme bottom (strongest low-side level)
      `is_strong_high` – True if high side is strong
      `is_strong_low`  – True if low side is strong
    """
    highs = df['high'].values
    lows = df['low'].values
    trend = df['trend'].values
    n = len(df)

    zone_top = np.full(n, np.nan)
    zone_bottom = np.full(n, np.nan)
    is_strong_high = np.zeros(n, dtype=bool)
    is_strong_low = np.zeros(n, dtype=bool)

    top = np.nan
    bottom = np.nan

    for i in range(n):
        # Update trailing
        if np.isnan(top) or highs[i] > top:
            top = highs[i]
        if np.isnan(bottom) or lows[i] < bottom:
            bottom = lows[i]

        # Reset on new pivot detection (swing_high/low level changes)
        if i > 0:
            sh_changed = (df['swing_high_level'].iat[i] != df['swing_high_level'].iat[i - 1]
                          and not np.isnan(df['swing_high_level'].iat[i]))
            sl_changed = (df['swing_low_level'].iat[i] != df['swing_low_level'].iat[i - 1]
                          and not np.isnan(df['swing_low_level'].iat[i]))
            if sh_changed:
                top = df['swing_high_level'].iat[i]
            if sl_changed:
                bottom = df['swing_low_level'].iat[i]

        zone_top[i] = top
        zone_bottom[i] = bottom
        is_strong_high[i] = trend[i] == BEARISH
        is_strong_low[i] = trend[i] == BULLISH

    df = df.copy()
    df['zone_top'] = zone_top
    df['zone_bottom'] = zone_bottom
    df['is_strong_high'] = is_strong_high
    df['is_strong_low'] = is_strong_low

    return df


# ─── 4. Valid Order Block Detection ──────────────────────────────────────────

def detect_valid_obs(df: pd.DataFrame, trend_filter: bool = False) -> pd.DataFrame:
    """
    Port of Pine 'Valid OB Detection' (stable.pine lines 527-572).

    3-candle pattern looked at from the CURRENT bar (bar[0]):
      bar[2] = OB candle (must sweep liquidity of bar[3])
      bar[1] = reaction candle
      bar[0] = FVG candle (must create fair value gap with bar[2])

    Bullish OB:
      - Sweep:  low[2]  < low[3]   (swept previous low)
      - FVG:    low[0]  > high[2]  (gap above OB)
      - Trend:  must be BULLISH

    Bearish OB:
      - Sweep:  high[2] > high[3]  (swept previous high)
      - FVG:    high[0] < low[2]   (gap below OB)
      - Trend:  must be BEARISH

    Adds columns:
      `valid_bull_ob` – True on bar[0] when a valid bullish OB is detected
      `valid_bear_ob` – True on bar[0] when a valid bearish OB is detected
      `ob_high`       – high of OB candle (bar[2])
      `ob_low`        – low  of OB candle (bar[2])
      `ob_bar_index`  – index of OB candle (bar[2])
    """
    highs = df['high'].values
    lows = df['low'].values
    trend = df['trend'].values
    n = len(df)

    valid_bull = np.zeros(n, dtype=bool)
    valid_bear = np.zeros(n, dtype=bool)
    ob_high = np.full(n, np.nan)
    ob_low = np.full(n, np.nan)
    ob_bar_idx = np.full(n, -1, dtype=int)

    for i in range(3, n):
        # Liquidity sweep at bar[2] (i-2)
        bull_sweep = lows[i - 2] < lows[i - 3]
        bear_sweep = highs[i - 2] > highs[i - 3]

        # FVG between bar[0] (i) and bar[2] (i-2)
        bull_fvg = lows[i] > highs[i - 2]
        bear_fvg = highs[i] < lows[i - 2]

        # Valid OB
        if bull_sweep and bull_fvg and (not trend_filter or trend[i] == BULLISH):
            valid_bull[i] = True
            ob_high[i] = highs[i - 2]
            ob_low[i] = lows[i - 2]
            ob_bar_idx[i] = i - 2

        if bear_sweep and bear_fvg and (not trend_filter or trend[i] == BEARISH):
            valid_bear[i] = True
            ob_high[i] = highs[i - 2]
            ob_low[i] = lows[i - 2]
            ob_bar_idx[i] = i - 2

    df = df.copy()
    df['valid_bull_ob'] = valid_bull
    df['valid_bear_ob'] = valid_bear
    df['ob_high'] = ob_high
    df['ob_low'] = ob_low
    df['ob_bar_index'] = ob_bar_idx

    return df


# ─── 5. OB Mitigation Tracking ──────────────────────────────────────────────

def track_ob_mitigation(df: pd.DataFrame,
                        max_obs: int = 100,
                        mitigation_type: str = 'High/Low'
                        ) -> pd.DataFrame:
    """
    Maintains a running list of active OBs and marks when price mitigates them.

    Mitigation:
      - Bullish OB mitigated when price LOW reaches into OB zone (low <= ob_high)
      - Bearish OB mitigated when price HIGH reaches into OB zone (high >= ob_low)

    Adds columns:
      `ob_mitigated_type`  – 'BULL' | 'BEAR' | NaN  (type of OB that was mitigated)
      `ob_mitigated_high`  – high of the mitigated OB
      `ob_mitigated_low`   – low  of the mitigated OB
      `ob_mitigated_idx`   – bar index where the OB candle was
    """
    highs = df['high'].values
    lows = df['low'].values
    closes = df['close'].values
    n = len(df)

    mit_type = np.full(n, None, dtype=object)
    mit_high = np.full(n, np.nan)
    mit_low = np.full(n, np.nan)
    mit_idx = np.full(n, -1, dtype=int)

    active_obs: List[ActiveOB] = []

    for i in range(n):
        # ── Add new OBs ──
        if df['valid_bull_ob'].iat[i]:
            ob = ActiveOB(
                ob_high=df['ob_high'].iat[i],
                ob_low=df['ob_low'].iat[i],
                bar_index=int(df['ob_bar_index'].iat[i]),
                bias=BULLISH
            )
            active_obs.insert(0, ob)
            if len(active_obs) > max_obs:
                active_obs.pop()

        if df['valid_bear_ob'].iat[i]:
            ob = ActiveOB(
                ob_high=df['ob_high'].iat[i],
                ob_low=df['ob_low'].iat[i],
                bar_index=int(df['ob_bar_index'].iat[i]),
                bias=BEARISH
            )
            active_obs.insert(0, ob)
            if len(active_obs) > max_obs:
                active_obs.pop()

        # ── Check mitigation ──
        # Use the mitigation source based on config
        bull_mit_src = closes[i] if mitigation_type == 'Close' else lows[i]
        bear_mit_src = closes[i] if mitigation_type == 'Close' else highs[i]

        to_remove = []
        for j, ob in enumerate(active_obs):
            if ob.bias == BULLISH:
                # Bullish OB is mitigated when price comes DOWN to the OB zone
                if bull_mit_src <= ob.ob_high and lows[i] <= ob.ob_high:
                    # Price touched the OB zone
                    if mit_type[i] is None:  # Only record first mitigation per bar
                        mit_type[i] = 'BULL'
                        mit_high[i] = ob.ob_high
                        mit_low[i] = ob.ob_low
                        mit_idx[i] = ob.bar_index
                    to_remove.append(j)
                # Full mitigation: price broke below OB entirely
                elif bull_mit_src < ob.ob_low:
                    to_remove.append(j)

            elif ob.bias == BEARISH:
                # Bearish OB is mitigated when price comes UP to the OB zone
                if bear_mit_src >= ob.ob_low and highs[i] >= ob.ob_low:
                    if mit_type[i] is None:
                        mit_type[i] = 'BEAR'
                        mit_high[i] = ob.ob_high
                        mit_low[i] = ob.ob_low
                        mit_idx[i] = ob.bar_index
                    to_remove.append(j)
                # Full mitigation: price broke above OB entirely
                elif bear_mit_src > ob.ob_high:
                    to_remove.append(j)

        # Remove mitigated OBs (reverse order to keep indices valid)
        for j in sorted(set(to_remove), reverse=True):
            active_obs.pop(j)

    df = df.copy()
    df['ob_mitigated_type'] = mit_type
    df['ob_mitigated_high'] = mit_high
    df['ob_mitigated_low'] = mit_low
    df['ob_mitigated_idx'] = mit_idx

    return df


# ─── Pipeline ────────────────────────────────────────────────────────────────

def compute_all_smc(df: pd.DataFrame, swing_length: int = 50, ob_trend_filter: bool = False) -> pd.DataFrame:
    """
    Run the full SMC indicator pipeline on a DataFrame.

    Expects columns: date, open, high, low, close, volume
    Returns a DataFrame with all SMC columns appended.
    """
    df = detect_swings(df, size=swing_length)
    df = detect_trend(df, size=swing_length)
    df = detect_zones(df)
    df = detect_valid_obs(df, trend_filter=ob_trend_filter)
    df = track_ob_mitigation(df)
    return df
