import math

# Constants
BULLISH_LEG = 1
BEARISH_LEG = 0
BULLISH = 1
BEARISH = -1

class Pivot:
    def __init__(self, current_level, last_level, crossed, bar_time, bar_index):
        self.current_level = current_level
        self.last_level = last_level
        self.crossed = crossed
        self.bar_time = bar_time
        self.bar_index = bar_index

    def __repr__(self):
        return f"Pivot(Level={self.current_level}, Time={self.bar_time}, Index={self.bar_index}, Crossed={self.crossed})"

class OrderBlock:
    def __init__(self, high, low, time, bias):
        self.high = high
        self.low = low
        self.time = time
        self.bias = bias # 1 for Bullish, -1 for Bearish

    def __repr__(self):
        bias_str = "Bullish" if self.bias == BULLISH else "Bearish"
        return f"{bias_str} OB(High={self.high}, Low={self.low}, Time={self.time})"

class SMCLogic:
    def __init__(self):
        self.swing_high = Pivot(None, None, False, 0, 0)
        self.swing_low = Pivot(None, None, False, 0, 0)
        self.trend = 0 # 0 for unknown/neutral
        self.order_blocks = []
        
        # Internal state for leg detection
        self.legs = [] # Stores leg direction for each bar

    def leg(self, highs, lows, size, current_index):
        """
        Determines leg direction based on local highs/lows.
        Pine Script logic: leg varies based on highest/lowest of 'size' bars.
        """
        if current_index < size:
            return 0 # Not enough data
        
        # Slice for the last 'size' bars including current
        # Note: In Pine, high[size] refers to the value 'size' bars ago.
        # We need to look at specific windows.
        # Pine: high[size] > ta.highest(size) -> checks if the high 'size' bars ago is higher than the max of last 'size' bars (excluding itself?)
        # Let's approximate the Pine logic:
        # Check if the bar at `current_index - size` is a local extreme.
        
        check_index = current_index - size
        if check_index < 0:
            return 0
            
        # Range for ta.highest(size) in Pine usually means the highest of the *current* window.
        # But here we are checking if a past bar was a pivot.
        
        # Let's simplify: A high is a high if it's the highest point in [index-size, index+size] logic usually.
        # The provided Pine code uses:
        # newLegHigh = high[size] > ta.highest(size)
        # This implies: High at (current - size) > Highest in (current-size+1 ... current)? 
        # Actually ta.highest(size) in Pine calculates highest of current bar back to size-1 bars.
        # So high[size] > ta.highest(size) means "High at T-size is greater than MAX(High T ... High T-size+1)"?
        # Let's implement a standard Pivot logic for Python to be robust.
        
        target_high = highs[check_index]
        target_low = lows[check_index]
        
        # Check left and right neighbors (simple pivot)
        # We only have data up to current_index.
        # So we check if highs[check_index] is max in highs[check_index-size : check_index+size]
        # But we can only verify up to current_index.
        
        # Strict translation of user's code:
        # newLegHigh = high[size] > ta.highest(size)
        # Python: highs[current_index - size] > max(highs[current_index-size+1 : current_index+1])
        
        window_highs = highs[current_index - size + 1 : current_index + 1]
        window_lows = lows[current_index - size + 1 : current_index + 1]
        
        is_highest = target_high > max(window_highs) if window_highs else False
        is_lowest = target_low < min(window_lows) if window_lows else False
        
        if is_highest:
            return BEARISH_LEG
        elif is_lowest:
            return BULLISH_LEG
        
        return 0 # Default / No change
        
    def get_structure(self, df, size=5):
        """
        Main loop to process data and detect structure.
        df: List of dictionaries or Objects with 'high', 'low', 'close', 'time'.
        """
        highs = [x['high'] for x in df]
        lows = [x['low'] for x in df]
        closes = [x['close'] for x in df]
        times = [x['time'] for x in df]
        
        results = []
        
        # State
        current_leg = 0
        prev_leg = 0
        
        for i in range(len(df)):
            # 1. Calculate Leg
            # We need at least 'size' bars to determine the leg for the bar at 'i-size'
            if i < size:
                results.append({'bar_index': i, 'event': None})
                continue
                
            # Logic applies to the point 'size' bars ago
            pivot_index = i - size
            
            # Determine logic for THIS bar.
            # In Pine, the script runs on every bar.
            # The 'leg' function checks if `high[size]` (bar at i-size) is a pivot.
            
            # We assume the user's Pine logic: 
            # if leg(size) changes, it means we found a new pivot at i-size.
            
            new_leg_state = self.leg(highs, lows, size, i)
            
            # Use specific logic from Pine to maintain state if no new pivot found?
            # Creating a simplified state machine here.
            
            if new_leg_state != 0:
                current_leg = new_leg_state
            
            # Detect change
            leg_changed = current_leg != prev_leg
            
            event = None
            
            if leg_changed:
                # New Pivot Found at pivot_index
                 # If we switched to Bullish Leg, it means we found a LOW.
                 # If we switched to Bearish Leg, it means we found a HIGH.
                 
                if current_leg == BULLISH_LEG:
                    # Found a LOW
                    self.swing_low.last_level = self.swing_low.current_level
                    self.swing_low.current_level = lows[pivot_index]
                    self.swing_low.bar_index = pivot_index
                    self.swing_low.bar_time = times[pivot_index]
                    self.swing_low.crossed = False
                    event = f"Swing Low at {lows[pivot_index]} (Index {pivot_index})"
                    
                elif current_leg == BEARISH_LEG:
                    # Found a HIGH
                    self.swing_high.last_level = self.swing_high.current_level
                    self.swing_high.current_level = highs[pivot_index]
                    self.swing_high.bar_index = pivot_index
                    self.swing_high.bar_time = times[pivot_index]
                    self.swing_high.crossed = False
                    event = f"Swing High at {highs[pivot_index]} (Index {pivot_index})"
            
            prev_leg = current_leg
            
            # Structure Break Detection (Market Structure)
            # Run this on the *current* bar (i), using the *latest known* pivot.
            
            current_close = closes[i]
            
            # Check for BOS/CHOCH
            # Bullish Break
            if self.swing_high.current_level is not None and current_close > self.swing_high.current_level and not self.swing_high.crossed:
                tag = "CHOCH" if self.trend == BEARISH else "BOS"
                self.trend = BULLISH
                self.swing_high.crossed = True
                event = f"Bullish {tag} at Index {i} (Price {current_close} > {self.swing_high.current_level})"
                
                # Create Order Block (Simplified: Just take the candle at pivot_index for demo)
                # Logic: Scan from pivot index to current index for lowest candle (Bullish OB)
                # For demo, just printing
                results.append({'bar_index': i, 'event': f"Created Bullish OB at pivot"})

            # Bearish Break
            if self.swing_low.current_level is not None and current_close < self.swing_low.current_level and not self.swing_low.crossed:
                tag = "CHOCH" if self.trend == BULLISH else "BOS"
                self.trend = BEARISH
                self.swing_low.crossed = True
                event = f"Bearish {tag} at Index {i} (Price {current_close} < {self.swing_low.current_level})"
                results.append({'bar_index': i, 'event': f"Created Bearish OB at pivot"})
            
            if event:
                results.append({'bar_index': i, 'event': event})
                
        return results
