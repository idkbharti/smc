import pandas as pd
import numpy as np
import math

# Constants
BULLISH = 1
BEARISH = -1

class Pivot:
    def __init__(self, current_level=None, last_level=None, crossed=False, bar_time=0, bar_index=0):
        self.current_level = current_level
        self.last_level = last_level
        self.crossed = crossed
        self.bar_time = bar_time
        self.bar_index = bar_index

class TrailingExtremes:
    def __init__(self, top=float('-inf'), bottom=float('inf'), bar_time=0, bar_index=0, last_top_time=0, last_bottom_time=0):
        self.top = top
        self.bottom = bottom
        self.bar_time = bar_time
        self.bar_index = bar_index
        self.last_top_time = last_top_time
        self.last_bottom_time = last_bottom_time

class OrderBlock:
    def __init__(self, high, low, time, bias, is_refined=False, tag=""):
        self.high = high
        self.low = low
        self.time = time
        self.bias = bias
        self.partial = False
        self.current_high = high
        self.current_low = low
        self.is_refined = is_refined
        self.tag = tag

class SMC_Core:
    def __init__(self, df: pd.DataFrame, swings_length=50, tag="15m"):
        """
        Expects a pandas DataFrame with columns: ['time', 'open', 'high', 'low', 'close']
        """
        self.df = df
        self.swings_length = swings_length
        self.tag = tag
        
        # State Arrays
        self.swing_high = Pivot()
        self.swing_low = Pivot()
        self.trailing = TrailingExtremes()
        self.swing_trend = 0
        
        # Lists to hold active Output Data
        self.obs = []       # Order Blocks
        self.trades = []    # Trade History
        
    def _leg(self, idx):
        if idx < self.swings_length:
            return -1
            
        # pine: high[size] > ta.highest(size)
        # Is the high `size` bars ago strictly greater than the maximum of the highs over the last `size` bars?
        
        target_idx = idx - self.swings_length
        target_high = self.df['high'].iloc[target_idx]
        target_low = self.df['low'].iloc[target_idx]
        
        # window from target_idx + 1 up to current idx (length = size)
        window_highs = self.df['high'].iloc[target_idx + 1: idx + 1]
        window_lows = self.df['low'].iloc[target_idx + 1: idx + 1]
        
        max_high = window_highs.max() if not window_highs.empty else float('-inf')
        min_low = window_lows.min() if not window_lows.empty else float('inf')
        
        if target_high > max_high:
            return 0  # Bearish Leg Starts (Found a High)
        elif target_low < min_low:
            return 1  # Bullish Leg Starts (Found a Low)
            
        return -1
        
    def _update_trailing(self, idx, high, low, time):
        if high > self.trailing.top:
            self.trailing.top = high
            self.trailing.last_top_time = time
            
        if low < self.trailing.bottom:
            self.trailing.bottom = low
            self.trailing.last_bottom_time = time
            
    def compute(self, df_lower_tf=None, lt_tf_tag=""):
        """
        Runs the full SMC backtest over the primary DataFrame.
        """
        leg_history = np.full(len(self.df), -1)
        
        for idx in range(len(self.df)):
            if idx < self.swings_length:
                continue
                
            row = self.df.iloc[idx]
            
            # 1. Update Trailing Extremes
            self._update_trailing(idx, row['high'], row['low'], row['time'])
            
            # 2. Get Structure (Leg)
            curr_leg = self._leg(idx)
            leg_history[idx] = curr_leg
            
            prev_leg = leg_history[idx-1]
            new_pivot = (curr_leg != -1) and (curr_leg != prev_leg)
            pivot_low = (curr_leg == 1) and (prev_leg != 1)
            pivot_high = (curr_leg == 0) and (prev_leg != 0)
            
            target_idx = idx - self.swings_length
            target_row = self.df.iloc[target_idx]
            
            if new_pivot:
                if self.swing_trend == 0:
                    self.swing_trend = BULLISH if pivot_low else BEARISH
                    
                if pivot_low:
                    self.swing_low.last_level = self.swing_low.current_level
                    self.swing_low.current_level = target_row['low']
                    self.swing_low.crossed = False
                    self.swing_low.bar_time = target_row['time']
                    self.swing_low.bar_index = target_idx
                    
                    self.trailing.bottom = target_row['low']
                    self.trailing.bar_time = target_row['time']
                    self.trailing.last_bottom_time = target_row['time']
                else:
                    self.swing_high.last_level = self.swing_high.current_level
                    self.swing_high.current_level = target_row['high']
                    self.swing_high.crossed = False
                    self.swing_high.bar_time = target_row['time']
                    self.swing_high.bar_index = target_idx
                    
                    self.trailing.top = target_row['high']
                    self.trailing.bar_time = target_row['time']
                    self.trailing.last_top_time = target_row['time']
                    
            # 3. Detect BOS/CHoCH
            if self.swing_high.current_level is not None and not pd.isna(self.swing_high.current_level):
                prev_close = self.df['close'].iloc[idx-1]
                # crossover
                if prev_close <= self.swing_high.current_level and row['close'] > self.swing_high.current_level and not self.swing_high.crossed:
                    self.swing_trend = BULLISH
                    self.swing_high.crossed = True
                    
            if self.swing_low.current_level is not None and not pd.isna(self.swing_low.current_level):
                prev_close = self.df['close'].iloc[idx-1]
                # crossunder
                if prev_close >= self.swing_low.current_level and row['close'] < self.swing_low.current_level and not self.swing_low.crossed:
                    self.swing_trend = BEARISH
                    self.swing_low.crossed = True
                    
            # 4. Filter OB Logic
            self._delete_obs(row['high'], row['low'], row['close'], row['time'])
            
            # Detect OB (Candle[2] Sweep + FVG on Candle[0])
            if idx >= 3:
                c2_low = self.df['low'].iloc[idx-2]
                c3_low = self.df['low'].iloc[idx-3]
                c2_high = self.df['high'].iloc[idx-2]
                c3_high = self.df['high'].iloc[idx-3]
                
                c0_low = row['low']
                c0_high = row['high']
                
                bull_sweep = c2_low < c3_low
                bear_sweep = c2_high > c3_high
                bull_fvg = c0_low > c2_high
                bear_fvg = c0_high < c2_low
                
                valid_bull_ob = bull_sweep and bull_fvg and self.swing_trend == BULLISH
                valid_bear_ob = bear_sweep and bear_fvg and self.swing_trend == BEARISH
                
                if valid_bull_ob:
                    ob = OrderBlock(c2_high, c2_low, self.df['time'].iloc[idx-2], BULLISH, tag=self.tag)
                    self.obs.insert(0, ob)
                    
                if valid_bear_ob:
                    ob = OrderBlock(c2_high, c2_low, self.df['time'].iloc[idx-2], BEARISH, tag=self.tag)
                    self.obs.insert(0, ob)
                    
            # 5. Nested / Lower Timeframe Analysis would go here (Refined OB matching)
            # Currently just mapping basic structure for the framework!
            
    def _delete_obs(self, curr_high, curr_low, curr_close, curr_time):
        """
        Handles OB mitigation (partial and full) on every tick/candle.
        Here we also bake in the 1:5 RR Entry execution upon FIRST tap!
        """
        # Close mitigation as defined
        bear_mitig_src = curr_close
        bull_mitig_src = curr_close
        
        to_remove = []
        for i, ob in enumerate(self.obs):
            if ob.bias == BEARISH:
                if curr_high > ob.high:
                    to_remove.append(ob)
                elif curr_high > ob.low:
                    if not ob.partial:
                        ob.partial = True
                        ob.current_low = curr_high
                        # === RECORD TRADE ===
                        self._log_trade(ob, curr_close, BEARISH, curr_time)
                    else:
                        ob.current_low = max(ob.current_low, curr_high)
            else:
                if curr_low < ob.low:
                    to_remove.append(ob)
                elif curr_low < ob.high:
                    if not ob.partial:
                        ob.partial = True
                        ob.current_high = curr_low
                        # === RECORD TRADE ===
                        self._log_trade(ob, curr_close, BULLISH, curr_time)
                    else:
                        ob.current_high = min(ob.current_high, curr_low)
                        
        for ob in to_remove:
            if ob in self.obs:
                self.obs.remove(ob)

    def _log_trade(self, ob, entry_price, direction, entry_time):
        # 1:5 RR Trade Details computation
        sl = ob.high if direction == BEARISH else ob.low
        risk = abs(entry_price - sl)
        tp = entry_price - (risk * 5) if direction == BEARISH else entry_price + (risk * 5)
        
        self.trades.append({
            'order_block_tag': ob.tag,
            'direction': 'SHORT' if direction == BEARISH else 'LONG',
            'entry_time': entry_time,
            'entry_price': entry_price,
            'stop_loss': sl,
            'take_profit': tp,
            'risk_amount': risk
        })
