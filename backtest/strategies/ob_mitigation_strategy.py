"""
OB Mitigation Strategy — SMC/ICT Backtesting.

Entry: Price enters a valid OB zone + 2-CANDLE confirmation:
  BULLISH: Hammer at/near bullish OB → NEXT candle is Bullish Engulfing → Enter
  BEARISH: Inverted Hammer at/near bearish OB → NEXT candle is Bearish Engulfing → Enter

The strategy keeps OBs "active" once detected and checks if price + confirmation
candles occur within those OB zones (not just on the exact mitigation bar).

SL placement:
  LONG  → below the hammer candle's low
  SHORT → above the inverted hammer candle's high
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Optional, Dict


@dataclass
class Trade:
    """A single trade record."""
    entry_bar: int
    entry_date: object
    entry_price: float
    direction: str          # 'LONG' or 'SHORT'
    sl_price: float
    sl_distance: float
    tp_1_2: float
    tp_1_3: float
    tp_1_4: float
    ob_high: float
    ob_low: float
    ob_type: str            # 'BULL' or 'BEAR'
    confirmation: str       # 'hammer+engulfing' or 'inv_hammer+engulfing'
    hammer_bar: int         # bar index of the hammer/inv_hammer
    engulfing_bar: int      # bar index of the engulfing candle
    # Outcomes (filled during backtest)
    exit_bar: int = -1
    exit_date: object = None
    exit_price: float = 0.0
    exit_reason: str = ''   # 'SL', 'TP_1_2', 'TP_1_3', 'TP_1_4', 'END'
    hit_1_2: bool = False
    hit_1_3: bool = False
    hit_1_4: bool = False
    max_favorable: float = 0.0
    max_adverse: float = 0.0


@dataclass
class PendingOB:
    """An OB zone that is being watched for confirmation entries."""
    ob_high: float
    ob_low: float
    bias: int       # 1 = BULL, -1 = BEAR
    created_bar: int
    mitigated: bool = False


class OBMitigationStrategy:
    """
    Strategy: OB zone reaction + 2-candle confirmation sequence.

    Maintains a list of active OBs. When price enters an OB zone and a
    2-candle confirmation sequence (hammer → engulfing) appears, an entry
    is triggered.

    BULLISH entry:
      1. Price is at/near a bullish OB (low touches or enters OB zone)
      2. A HAMMER candle forms (bar i-2)
      3. The NEXT candle is a BULLISH ENGULFING (bar i-1)
      4. Enter at bar i's open
      5. SL below the HAMMER candle's low

    BEARISH entry:
      1. Price is at/near a bearish OB (high touches or enters OB zone)
      2. An INVERTED HAMMER candle forms (bar i-2)
      3. The NEXT candle is a BEARISH ENGULFING (bar i-1)
      4. Enter at bar i's open
      5. SL above the INVERTED HAMMER candle's high
    """

    def __init__(self, max_active_obs: int = 100):
        self.position: Optional[str] = None
        self.current_trade: Optional[Trade] = None
        self.completed_trades: List[Trade] = []
        self.active_obs: List[PendingOB] = []
        self.max_active_obs = max_active_obs

    def reset(self):
        self.position = None
        self.current_trade = None
        self.completed_trades = []
        self.active_obs = []

    def _update_obs(self, i: int, df: pd.DataFrame):
        """Add new valid OBs and remove fully mitigated ones."""
        # Add new bullish OBs
        if df['valid_bull_ob'].iat[i]:
            ob = PendingOB(
                ob_high=df['ob_high'].iat[i],
                ob_low=df['ob_low'].iat[i],
                bias=1,
                created_bar=i,
            )
            self.active_obs.insert(0, ob)

        # Add new bearish OBs
        if df['valid_bear_ob'].iat[i]:
            ob = PendingOB(
                ob_high=df['ob_high'].iat[i],
                ob_low=df['ob_low'].iat[i],
                bias=-1,
                created_bar=i,
            )
            self.active_obs.insert(0, ob)

        # Cap
        if len(self.active_obs) > self.max_active_obs:
            self.active_obs = self.active_obs[:self.max_active_obs]

        # Remove fully mitigated OBs (price completely broke through)
        high_val = df['high'].iat[i]
        low_val = df['low'].iat[i]

        to_remove = []
        for j, ob in enumerate(self.active_obs):
            if ob.bias == 1:   # Bull OB: remove if price broke below OB entirely
                if low_val < ob.ob_low:
                    to_remove.append(j)
            elif ob.bias == -1:  # Bear OB: remove if price broke above OB entirely
                if high_val > ob.ob_high:
                    to_remove.append(j)
        for j in sorted(to_remove, reverse=True):
            self.active_obs.pop(j)

    def _is_at_bull_ob(self, bar_idx: int, df: pd.DataFrame) -> Optional[PendingOB]:
        """Check if bar's price range touches any active bullish OB zone."""
        low_val = df['low'].iat[bar_idx]
        high_val = df['high'].iat[bar_idx]

        for ob in self.active_obs:
            if ob.bias == 1:
                # Price low should touch or enter the OB zone
                # OB zone is [ob_low, ob_high] — price dips into it
                if low_val <= ob.ob_high and high_val >= ob.ob_low:
                    return ob
        return None

    def _is_at_bear_ob(self, bar_idx: int, df: pd.DataFrame) -> Optional[PendingOB]:
        """Check if bar's price range touches any active bearish OB zone."""
        low_val = df['low'].iat[bar_idx]
        high_val = df['high'].iat[bar_idx]

        for ob in self.active_obs:
            if ob.bias == -1:
                # Price high should touch or enter the OB zone
                if high_val >= ob.ob_low and low_val <= ob.ob_high:
                    return ob
        return None

    def check_entry(self, i: int, df: pd.DataFrame) -> Optional[Trade]:
        """
        Check if bar `i` should trigger an entry.

        2-candle sequence:
          bar[i-2] = hammer/inv_hammer (reaction at OB zone)
          bar[i-1] = engulfing (confirmation)
          bar[i]   = entry bar

        The hammer candle must be at/touching an active OB zone.
        """
        if self.position is not None:
            return None
        if i < 3:
            return None

        # Update active OBs with this bar
        self._update_obs(i, df)

        hammer_bar = i - 2
        engulfing_bar = i - 1

        # ── BULLISH: hammer[i-2] at bull OB + bull_engulfing[i-1] ──
        if (df['bull_hammer'].iat[hammer_bar]
                and df['bull_engulfing'].iat[engulfing_bar]):
            # Check if the hammer candle was at a bullish OB
            ob = self._is_at_bull_ob(hammer_bar, df)
            if ob is not None:
                sl_price = df['low'].iat[hammer_bar]
                entry_price = df['open'].iat[i]
                sl_distance = entry_price - sl_price

                if sl_distance > 0:
                    # Remove this OB (used up)
                    if ob in self.active_obs:
                        self.active_obs.remove(ob)

                    return Trade(
                        entry_bar=i,
                        entry_date=df['date'].iat[i] if 'date' in df.columns else i,
                        entry_price=entry_price,
                        direction='LONG',
                        sl_price=sl_price,
                        sl_distance=sl_distance,
                        tp_1_2=entry_price + sl_distance * 2,
                        tp_1_3=entry_price + sl_distance * 3,
                        tp_1_4=entry_price + sl_distance * 4,
                        ob_high=ob.ob_high,
                        ob_low=ob.ob_low,
                        ob_type='BULL',
                        confirmation='hammer+engulfing',
                        hammer_bar=hammer_bar,
                        engulfing_bar=engulfing_bar,
                    )

        # ── BEARISH: inv_hammer[i-2] at bear OB + bear_engulfing[i-1] ──
        if (df['bear_inv_hammer'].iat[hammer_bar]
                and df['bear_engulfing'].iat[engulfing_bar]):
            ob = self._is_at_bear_ob(hammer_bar, df)
            if ob is not None:
                sl_price = df['high'].iat[hammer_bar]
                entry_price = df['open'].iat[i]
                sl_distance = sl_price - entry_price

                if sl_distance > 0:
                    if ob in self.active_obs:
                        self.active_obs.remove(ob)

                    return Trade(
                        entry_bar=i,
                        entry_date=df['date'].iat[i] if 'date' in df.columns else i,
                        entry_price=entry_price,
                        direction='SHORT',
                        sl_price=sl_price,
                        sl_distance=sl_distance,
                        tp_1_2=entry_price - sl_distance * 2,
                        tp_1_3=entry_price - sl_distance * 3,
                        tp_1_4=entry_price - sl_distance * 4,
                        ob_high=ob.ob_high,
                        ob_low=ob.ob_low,
                        ob_type='BEAR',
                        confirmation='inv_hammer+engulfing',
                        hammer_bar=hammer_bar,
                        engulfing_bar=engulfing_bar,
                    )

        return None

    def check_exit(self, i: int, df: pd.DataFrame) -> bool:
        """
        Check if bar `i` triggers an exit. Tracks 1:2, 1:3, 1:4 and SL.
        """
        if self.current_trade is None:
            return False

        # Still update OBs each bar
        self._update_obs(i, df)

        trade = self.current_trade
        high = df['high'].iat[i]
        low = df['low'].iat[i]

        if trade.direction == 'LONG':
            favorable = high - trade.entry_price
            adverse = trade.entry_price - low
            trade.max_favorable = max(trade.max_favorable, favorable)
            trade.max_adverse = max(trade.max_adverse, adverse)

            if high >= trade.tp_1_2:
                trade.hit_1_2 = True
            if high >= trade.tp_1_3:
                trade.hit_1_3 = True
            if high >= trade.tp_1_4:
                trade.hit_1_4 = True

            if low <= trade.sl_price:
                trade.exit_bar = i
                trade.exit_date = df['date'].iat[i] if 'date' in df.columns else i
                trade.exit_price = trade.sl_price
                trade.exit_reason = 'SL'
                self._close_trade()
                return True

            if trade.hit_1_4:
                trade.exit_bar = i
                trade.exit_date = df['date'].iat[i] if 'date' in df.columns else i
                trade.exit_price = trade.tp_1_4
                trade.exit_reason = 'TP_1_4'
                self._close_trade()
                return True

        elif trade.direction == 'SHORT':
            favorable = trade.entry_price - low
            adverse = high - trade.entry_price
            trade.max_favorable = max(trade.max_favorable, favorable)
            trade.max_adverse = max(trade.max_adverse, adverse)

            if low <= trade.tp_1_2:
                trade.hit_1_2 = True
            if low <= trade.tp_1_3:
                trade.hit_1_3 = True
            if low <= trade.tp_1_4:
                trade.hit_1_4 = True

            if high >= trade.sl_price:
                trade.exit_bar = i
                trade.exit_date = df['date'].iat[i] if 'date' in df.columns else i
                trade.exit_price = trade.sl_price
                trade.exit_reason = 'SL'
                self._close_trade()
                return True

            if trade.hit_1_4:
                trade.exit_bar = i
                trade.exit_date = df['date'].iat[i] if 'date' in df.columns else i
                trade.exit_price = trade.tp_1_4
                trade.exit_reason = 'TP_1_4'
                self._close_trade()
                return True

        return False

    def enter(self, trade: Trade):
        self.position = trade.direction
        self.current_trade = trade

    def _close_trade(self):
        if self.current_trade:
            self.completed_trades.append(self.current_trade)
        self.position = None
        self.current_trade = None

    def force_close(self, i: int, df: pd.DataFrame):
        if self.current_trade:
            trade = self.current_trade
            trade.exit_bar = i
            trade.exit_date = df['date'].iat[i] if 'date' in df.columns else i
            trade.exit_price = df['close'].iat[i]
            trade.exit_reason = 'END'
            self._close_trade()
