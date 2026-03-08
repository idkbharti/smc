import pandas as pd
import numpy as np
import MetaTrader5 as mt5

# Constants
BULLISH = 1
BEARISH = -1

class OB:
    """Order Block – mirrors stable.pine `orderBlock` type."""
    __slots__ = ('high','low','time','bias','partial','cur_h','cur_l','mitigated','is_refined')
    def __init__(self, high, low, time, bias):
        self.high=high; self.low=low; self.time=time; self.bias=bias
        self.partial=False; self.mitigated=False
        self.cur_h=high; self.cur_l=low
        self.is_refined=False

class StructureEvent:
    __slots__ = ('kind','level','time','direction')
    def __init__(self, kind, level, time, direction):
        self.kind=kind; self.level=level; self.time=time; self.direction=direction

class SMCEngine:
    """
    Mirrors stable.pine logic:
      • leg()            – high[size] > highest(size) → bearish leg start
      • Trailing extremes– trailing.top = max(high), trailing.bottom = min(low)
      • BOS/CHoCH        – price crossover of swing pivots
      • OB detection     – bar[-2] sweep + FVG
    """
    def __init__(self, length: int = 20, rr: float = 3.0):
        self.length = length
        self.rr     = rr
        
        # Swing pivot state
        self.sh_level    = None
        self.sh_last     = None
        self.sh_time     = None
        self.sh_crossed  = False
        self.sl_level    = None
        self.sl_last     = None
        self.sl_time     = None
        self.sl_crossed  = False
        self.trend       = 0

        # Trailing extremes
        self.trail_top         = None
        self.trail_bottom      = None
        self.trail_top_time    = None
        self.trail_bot_time    = None

        # Output arrays
        self.obs       = []
        self.structure = []
        self.trades    = []

    def _reset_state(self):
        # Swing pivot state
        self.sh_level    = None
        self.sh_last     = None
        self.sh_time     = None
        self.sh_crossed  = False
        self.sl_level    = None
        self.sl_last     = None
        self.sl_time     = None
        self.sl_crossed  = False
        self.trend       = 0

        # Trailing extremes
        self.trail_top         = None
        self.trail_bottom      = None
        self.trail_top_time    = None
        self.trail_bot_time    = None

        # Output arrays
        self.obs       = []
        self.structure = []
        self.trades    = []

    @staticmethod
    def _leg(H, L, idx, size):
        """
        Detects swing pivots with a look-back and look-forward window of 'size'.
        """
        if idx < size * 2: return -1
        
        target_idx = idx - size
        pivot_h = H[target_idx]
        pivot_l = L[target_idx]
        
        # Look-back window [target_idx - size : target_idx]
        prev_h = H[target_idx - size : target_idx]
        prev_l = L[target_idx - size : target_idx]
        # Look-forward window [target_idx + 1 : target_idx + size + 1]
        next_h = H[target_idx + 1 : target_idx + size + 1]
        next_l = L[target_idx + 1 : target_idx + size + 1]
        
        if len(prev_h) == 0 or len(next_h) == 0: return -1
        
        # Bullish Pivot (Swing Low)
        if pivot_l < prev_l.min() and pivot_l < next_l.min():
            return 1
        # Bearish Pivot (Swing High)
        if pivot_h > prev_h.max() and pivot_h > next_h.max():
            return 0
            
        return -1

    def update(self, df: pd.DataFrame, rr: float = None):
        if rr is not None: self.rr = rr
        self._reset_state()

        H = df['high'].values
        L = df['low'].values
        C = df['close'].values
        T = df['time'].values
        n = len(df)
        size = self.length
        prev_leg = -1

        for i in range(n):
            h, l, c, t = H[i], L[i], C[i], T[i]

            # Resolve open trades
            for tr in self.trades:
                if tr['result'] == 'open':
                    if tr['dir'] == 'LONG':
                        if h >= tr['tp']:  tr['result'] = 'win'
                        elif l <= tr['sl']: tr['result'] = 'loss'
                    else:
                        if l <= tr['tp']:  tr['result'] = 'win'
                        elif h >= tr['sl']: tr['result'] = 'loss'

            # updateTrailingExtremes
            if self.trail_top is None or h > self.trail_top:
                self.trail_top      = h
                self.trail_top_time = t
            if self.trail_bottom is None or l < self.trail_bottom:
                self.trail_bottom   = l
                self.trail_bot_time = t

            # getCurrentStructure
            cur_leg = self._leg(H, L, i, size)
            new_pivot       = (cur_leg != -1 and cur_leg != prev_leg)
            pivot_low       = (cur_leg == 1)

            if new_pivot:
                pi = i - size
                if self.trend == 0:
                    self.trend = BULLISH if pivot_low else BEARISH

                if pivot_low:
                    self.sl_last   = self.sl_level
                    self.sl_level  = L[pi]
                    self.sl_time   = T[pi]
                    self.sl_crossed = False
                    self.trail_bottom   = L[pi]
                    self.trail_bot_time = T[pi]
                else:
                    self.sh_last   = self.sh_level
                    self.sh_level  = H[pi]
                    self.sh_time   = T[pi]
                    self.sh_crossed = False
                    self.trail_top      = H[pi]
                    self.trail_top_time = T[pi]

            if cur_leg != -1:
                prev_leg = cur_leg

            # displayStructure – BOS / CHoCH
            if i > 0:
                pc = C[i-1]
                if (self.sh_level is not None and not self.sh_crossed
                        and pc <= self.sh_level and c > self.sh_level):
                    kind = 'CHoCH' if self.trend == BEARISH else 'BOS'
                    self.trend      = BULLISH
                    self.sh_crossed = True
                    self.structure.append(StructureEvent(kind, self.sh_level, t, BULLISH))

                if (self.sl_level is not None and not self.sl_crossed
                        and pc >= self.sl_level and c < self.sl_level):
                    kind = 'CHoCH' if self.trend == BULLISH else 'BOS'
                    self.trend      = BEARISH
                    self.sl_crossed = True
                    self.structure.append(StructureEvent(kind, self.sl_level, t, BEARISH))

            # OB detection
            if i >= 3:
                c2h, c2l = H[i-2], L[i-2]
                c3h, c3l = H[i-3], L[i-3]
                bull_sweep = c2l < c3l
                bull_fvg   = l  > c2h
                bear_sweep = c2h > c3h
                bear_fvg   = h  < c2l
                ob_time    = T[i-2]

                if bull_sweep and bull_fvg and self.trend == BULLISH:
                    if not any(ob.time == ob_time and ob.bias == BULLISH for ob in self.obs):
                        new_ob = OB(c2h, c2l, ob_time, BULLISH)
                        # Nested/Refined detection
                        if any(ob.bias == BULLISH and not ob.mitigated and ob.time < new_ob.time and 
                               new_ob.high <= ob.high and new_ob.low >= ob.low for ob in self.obs):
                            new_ob.is_refined = True
                        self.obs.insert(0, new_ob)

                if bear_sweep and bear_fvg and self.trend == BEARISH:
                    if not any(ob.time == ob_time and ob.bias == BEARISH for ob in self.obs):
                        new_ob = OB(c2h, c2l, ob_time, BEARISH)
                        # Nested/Refined detection
                        if any(ob.bias == BEARISH and not ob.mitigated and ob.time < new_ob.time and 
                               new_ob.high <= ob.high and new_ob.low >= ob.low for ob in self.obs):
                            new_ob.is_refined = True
                        self.obs.insert(0, new_ob)

            # Mitigation
            for ob in self.obs:
                if ob.mitigated: continue # Already greyed out

                if ob.bias == BEARISH:
                    # Full Mitigation (Body Close Above)
                    if c > ob.high:
                        ob.mitigated = True
                    # Partial Mitigation (Wick Sweep)
                    elif h > ob.low:
                        if not ob.partial:
                            ob.cur_h = ob.high; ob.cur_l = h
                            self._log(ob, c, BEARISH, t)
                        else:
                            ob.cur_l = max(ob.cur_l, h)
                        ob.partial = True
                else:
                    # Full Mitigation (Body Close Below)
                    if c < ob.low:
                        ob.mitigated = True
                    # Partial Mitigation (Wick Sweep)
                    elif l < ob.high:
                        if not ob.partial:
                            ob.cur_h = l; ob.cur_l = ob.low
                            self._log(ob, c, BULLISH, t)
                        else:
                            ob.cur_h = min(ob.cur_h, l)
                        ob.partial = True

    def _log(self, ob, entry, direction, t, live=False, symbol="EURUSD", lot=0.1):
        sl   = ob.high if direction == BEARISH else ob.low
        risk = abs(entry - sl)
        if risk == 0: return
        tp = entry - risk * self.rr if direction == BEARISH else entry + risk * self.rr
        
        trade_dir = 'SHORT' if direction == BEARISH else 'LONG'
        self.trades.append({
            'time':   t,
            'dir':    trade_dir,
            'entry':  entry,
            'sl':     sl,
            'tp':     tp,
            'result': 'open'
        })
        
        if live:
            order_type = mt5.ORDER_TYPE_SELL if trade_dir == 'SHORT' else mt5.ORDER_TYPE_BUY
            info = mt5.symbol_info(symbol)
            if not info: return
            price = mt5.symbol_info_tick(symbol).bid if trade_dir == 'SHORT' else mt5.symbol_info_tick(symbol).ask

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": float(lot),
                "type": order_type,
                "price": price,
                "sl": float(sl),
                "tp": float(tp),
                "deviation": 20,
                "magic": 234000,
                "comment": f"SMC OB {ob.time}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            mt5.order_send(request)
