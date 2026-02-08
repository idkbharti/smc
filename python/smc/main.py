"""
Main Entry Point for SMC Python Library.
Simulates a run over historical data.
"""

import sys
import os
import random

# Ensure we can import from local package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from python.smc.constants import *
from python.smc.smc_types import *
from python.smc.functions.get_current_structure import get_current_structure
from python.smc.functions.display_structure import display_structure

def generate_dummy_data(length=100):
    highs = []
    lows = []
    opens = []
    closes = []
    times = []
    
    price = 100.0
    for i in range(length):
        change = random.uniform(-2, 2)
        open_p = price
        close_p = price + change
        high_p = max(open_p, close_p) + random.uniform(0, 1)
        low_p = min(open_p, close_p) - random.uniform(0, 1)
        
        opens.append(open_p)
        closes.append(close_p)
        highs.append(high_p)
        lows.append(low_p)
        times.append(1600000000 + i * 60) # Fake timestamps
        
        price = close_p
        
    return opens, highs, lows, closes, times

def main():
    print("Initializing SMC Logic...")
    
    # 1. Setup Data
    opens, highs, lows, closes, times = generate_dummy_data(200)
    
    # 2. Setup State
    settings = Settings()
    settings.showSwingsInput = True
    settings.showStructureInput = True
    settings.showInternalsInput = True
    
    alerts = Alerts()
    trailing = TrailingExtremes()
    
    # Pivots
    swing_high = Pivot()
    swing_low = Pivot()
    internal_high = Pivot()
    internal_low = Pivot()
    equal_high = Pivot()
    equal_low = Pivot()
    
    # Trends
    swing_trend = Trend()
    internal_trend = Trend()
    
    # Display Objects
    equal_high_display = EqualDisplay()
    equal_low_display = EqualDisplay()
    
    # Arrays
    swing_obs = []
    internal_obs = []
    parsed_highs = highs # Using same list for simplicity
    parsed_lows = lows
    
    # State variables
    swing_leg_direction = 0
    internal_leg_direction = 0
    atr = 1.0 # Mock ATR
    
    print("Running Loop...")
    
    all_drawings = []
    
    for i in range(50, len(times)): # Start after some warm-up
        # 1. Get Current Structure (Swing)
        # SMC.getCurrentStructure(swingsLengthInput, false, false, ...)
        res_swing = get_current_structure(
            size=10, 
            equal_high_low=False, 
            internal=False, 
            settings=settings, 
            alerts=alerts, 
            trailing=trailing, 
            internal_low=internal_low, internal_high=internal_high, 
            swing_low=swing_low, swing_high=swing_high, 
            equal_low=equal_low, equal_high=equal_high, 
            atr_measure=atr, 
            equal_low_display=equal_low_display, equal_high_display=equal_high_display,
            high=highs, low=lows, times=times, current_index=i,
            previous_leg_direction=swing_leg_direction
        )
        
        swing_leg_direction = res_swing["new_leg_direction"]
        all_drawings.extend(res_swing["drawings"])
        
        # 2. Get Current Structure (Internal)
        # SMC.getCurrentStructure(5, false, true, ...)
        res_internal = get_current_structure(
            size=5, 
            equal_high_low=False, 
            internal=True, 
            settings=settings, 
            alerts=alerts, 
            trailing=trailing, 
            internal_low=internal_low, internal_high=internal_high, 
            swing_low=swing_low, swing_high=swing_high, 
            equal_low=equal_low, equal_high=equal_high, 
            atr_measure=atr, 
            equal_low_display=equal_low_display, equal_high_display=equal_high_display,
            high=highs, low=lows, times=times, current_index=i,
            previous_leg_direction=internal_leg_direction
        )
        
        internal_leg_direction = res_internal["new_leg_direction"]
        all_drawings.extend(res_internal["drawings"])
        
        # 3. Display Structure
        # SMC.displayStructure(true, ...)
        drawings_structure_internal = display_structure(
            internal=True, settings=settings, alerts=alerts,
            internal_high=internal_high, swing_high=swing_high,
            internal_low=internal_low, swing_low=swing_low,
            internal_trend=internal_trend, swing_trend=swing_trend,
            internal_order_blocks=internal_obs, swing_order_blocks=swing_obs,
            parsed_highs=highs, parsed_lows=lows, times=times,
            current_high=highs[i], current_low=lows[i], current_close=closes[i], current_open=opens[i],
            current_time=times[i], current_index=i
        )
        all_drawings.extend(drawings_structure_internal)
        
        drawings_structure_swing = display_structure(
            internal=False, settings=settings, alerts=alerts,
            internal_high=internal_high, swing_high=swing_high,
            internal_low=internal_low, swing_low=swing_low,
            internal_trend=internal_trend, swing_trend=swing_trend,
            internal_order_blocks=internal_obs, swing_order_blocks=swing_obs,
            parsed_highs=highs, parsed_lows=lows, times=times,
            current_high=highs[i], current_low=lows[i], current_close=closes[i], current_open=opens[i],
            current_time=times[i], current_index=i
        )
        all_drawings.extend(drawings_structure_swing)
        
    print(f"Simulation Complete.")
    print(f"Total Drawings Generated: {len(all_drawings)}")
    print(f"Internal OBs Identified: {len(internal_obs)}")
    print(f"Swing OBs Identified: {len(swing_obs)}")
    
    if all_drawings:
        print("Sample Drawing:", all_drawings[-1])

if __name__ == "__main__":
    main()
