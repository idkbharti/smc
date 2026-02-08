"""
Original Pine Script:
export getCurrentStructure(int size, bool equalHighLow, bool internal, Settings settings, Alerts alerts, TrailingExtremes trailing, Pivot internalLow, Pivot internalHigh, Pivot swingLow, Pivot swingHigh, Pivot equalLow, Pivot equalHigh, float atrMeasure, EqualDisplay equalLowDisplay, EqualDisplay equalHighDisplay) =>
    currentLeg = leg(size)
    newPivot = startOfNewLeg(currentLeg)
    ...
"""

from typing import List, Dict, Any
from ..smc_types import Pivot, Settings, Alerts, TrailingExtremes, EqualDisplay
from ..constants import BULLISH_LEG, BEARISH_LEG
from .leg import leg
from .leg_changes import start_of_new_leg, start_of_bullish_leg, start_of_bearish_leg
from .draw_equal_high_low import draw_equal_high_low
from .draw_label import draw_label

def get_current_structure(
    size: int, 
    equal_high_low: bool, 
    internal: bool, 
    settings: Settings, 
    alerts: Alerts, 
    trailing: TrailingExtremes, 
    internal_low: Pivot, 
    internal_high: Pivot, 
    swing_low: Pivot, 
    swing_high: Pivot, 
    equal_low: Pivot, 
    equal_high: Pivot, 
    atr_measure: float, 
    equal_low_display: EqualDisplay, 
    equal_high_display: EqualDisplay,
    high: List[float],
    low: List[float],
    times: List[int],
    current_index: int,
    previous_leg_direction: int
) -> Dict[str, Any]:
    """
    Main loop function. Updates pivots based on leg detection.
    Returns: Dictionary with 'drawings' list and 'new_leg_direction'.
    """
    
    drawings = []
    
    # 1. Detect Leg Direction
    # We pass the previous leg direction to maintain state if no change
    current_leg = leg(high, low, size, current_index, previous_leg_direction)
    
    # 2. Check for Changes
    is_new_pivot = start_of_new_leg(current_leg, previous_leg_direction)
    is_pivot_low = start_of_bullish_leg(current_leg, previous_leg_direction)
    is_pivot_high = start_of_bearish_leg(current_leg, previous_leg_direction)
    
    if is_new_pivot:
        # PINE: high[size] / low[size] / time[size]
        # In Python: high[current_index - size]
        prev_idx = current_index - size
        if prev_idx < 0:
            return {"drawings": [], "new_leg_direction": current_leg} 
            
        current_level_low = low[prev_idx]
        current_level_high = high[prev_idx]
        current_time_prev = times[prev_idx]
        
        if is_pivot_low:
            # Determine which Pivot object to update
            # Pivot p_ivot = equalHighLow ? equalLow : internal ? internalLow : swingLow
            if equal_high_low:
                p_ivot = equal_low
            elif internal:
                p_ivot = internal_low
            else:
                p_ivot = swing_low
                
            # Equal Lows Logic
            # math.abs(p_ivot.currentLevel - low[size]) < threshold
            # Note: p_ivot.currentLevel is the *previous* pivot level before we update it below
            if equal_high_low and abs(p_ivot.currentLevel - current_level_low) < (settings.equalHighsLowsThresholdInput * atr_measure):
                 draw_equal_high_low(p_ivot, current_level_low, size, False, settings, equal_low_display, current_time_prev, current_index)
                 alerts.equalLows = True
                 # We probably want to add the updated display objects to drawings?
                 # draw_equal_high_low updates equal_low_display in place.
                 # The visual system would need to read `equal_low_display`.
            
            # Update Pivot Object
            p_ivot.lastLevel = p_ivot.currentLevel
            p_ivot.currentLevel = current_level_low
            p_ivot.crossed = False
            p_ivot.barTime = current_time_prev
            p_ivot.barIndex = prev_idx
            
            # Trailing Update
            if not equal_high_low and not internal:
                trailing.bottom = p_ivot.currentLevel
                trailing.barTime = p_ivot.barTime
                trailing.barIndex = p_ivot.barIndex
                trailing.lastBottomTime = p_ivot.barTime
                
            # Show Swings Label
            if settings.showSwingsInput and not internal and not equal_high_low:
                tag = 'LL' if p_ivot.currentLevel < p_ivot.lastLevel else 'HL'
                # drawLabel(time[size], ...)
                lbl = draw_label(current_time_prev, p_ivot.currentLevel, tag, settings.swingBullishColor, "label_up", settings.modeInput)
                drawings.append(lbl)
                
        elif is_pivot_high: # Else branch in Pine implies is_pivot_high if is_new_pivot is true
             # Pivot p_ivot = equalHighLow ? equalHigh : internal ? internalHigh : swingHigh
            if equal_high_low:
                p_ivot = equal_high
            elif internal:
                p_ivot = internal_high
            else:
                p_ivot = swing_high
                
            # Equal Highs Logic
            if equal_high_low and abs(p_ivot.currentLevel - current_level_high) < (settings.equalHighsLowsThresholdInput * atr_measure):
                draw_equal_high_low(p_ivot, current_level_high, size, True, settings, equal_high_display, current_time_prev, current_index)
                alerts.equalHighs = True
                
            # Update Pivot Object
            p_ivot.lastLevel = p_ivot.currentLevel
            p_ivot.currentLevel = current_level_high
            p_ivot.crossed = False
            p_ivot.barTime = current_time_prev
            p_ivot.barIndex = prev_idx
            
            # Trailing Update
            if not equal_high_low and not internal:
                trailing.top = p_ivot.currentLevel
                trailing.barTime = p_ivot.barTime
                trailing.barIndex = p_ivot.barIndex
                trailing.lastTopTime = p_ivot.barTime
                
            # Show Swings Label
            if settings.showSwingsInput and not internal and not equal_high_low:
                tag = 'HH' if p_ivot.currentLevel > p_ivot.lastLevel else 'LH'
                lbl = draw_label(current_time_prev, p_ivot.currentLevel, tag, settings.swingBearishColor, "label_down", settings.modeInput)
                drawings.append(lbl)
                
    return {"drawings": drawings, "new_leg_direction": current_leg}
