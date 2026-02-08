"""
Original Pine Script:
// Function: leg
// Description: Determines if a bar is a local high or low relative to 'size' bars.
export leg(int size) =>
    var leg = 0
    newLegHigh = high[size] > ta.highest(size)
    newLegLow = low[size] < ta.lowest(size)
    if newLegHigh
        leg := BEARISH_LEG
    else if newLegLow
        leg := BULLISH_LEG
    leg
"""

from typing import List
from ..constants import BEARISH_LEG, BULLISH_LEG

def leg(high: List[float], low: List[float], size: int, current_index: int, previous_leg: int) -> int:
    """
    Determines if the bar at `current_index` indicates a new leg direction.
    
    Args:
        high: List of high prices.
        low: List of low prices.
        size: Lookback size for determining local extremes.
        current_index: The index of the *current* bar being processed.
                       Note: The Pine Script logic uses `high[size]` relative to current bar.
                       If we are processing bar at `current_index`, `high[size]` refers to `high[current_index - size]`.
                       And `ta.highest(size)` refers to highest in range `[current_index - size + 1, current_index]`.
                       Wait, Pine Script `ta.highest(source, length)` calculates highest value for the given length.
                       `ta.highest(size)` usually implies `ta.highest(high, size)`.
                       
                       Re-evaluating Pine Logic:
                       `high[size]` is the high `size` bars ago.
                       `ta.highest(size)` is the highest high of the *last* `size` bars (including current).
                       
                       Actually, `ta.highest(length)`: "Highest value of `source` for `length` bars back."
                       If called without source, it uses high? No, `ta.highest(length)` is `ta.highest(high, length)`.
                       
                       Let's look at `newLegHigh = high[size] > ta.highest(size)`.
                       In Pine, `high[size]` is the value at index `current - size`.
                       `ta.highest(size)` at `current` index is max of `high[current]...high[current - size + 1]`.
                       So it checks if the high `size` bars ago is higher than any high since then (up to current).
                       
                       This effectively checks if `high[current - size]` is a local maximum over the window of `size` bars to the right.
                       
    Returns:
        The new leg direction (BULLISH_LEG or BEARISH_LEG).
    """
    
    # We need at least `size` bars of history + `size` bars lookforward (implied by the logic waiting for confirmation).
    # But this function is called on every bar.
    # In Pine, `high[size]` accesses past data.
    # We must ensure `current_index - size` is valid.
    
    if current_index < size:
        return previous_leg

    # Logic:
    # Check if the bar at 'current_index - size' is a fractal high/low relative to the *subsequent* 'size' bars.
    # The 'ta.highest(size)' includes the current bar? Yes.
    
    # Pine: high[size] > ta.highest(size)
    # Python equivalent:
    # value_at_lag = high[current_index - size]
    # highest_in_window = max(high[current_index - size + 1 : current_index + 1])
    
    # Wait, ta.highest(size) is max(high[0], high[1], ..., high[size-1]) relative to current.
    # So range is `[current_index - size + 1, current_index]`.
    
    value_at_lag_high = high[current_index - size]
    
    # We need to be careful with slice indices.
    # range end is exclusive.
    # window: from (current_index - size + 1) to (current_index) inclusive.
    window_highs = high[current_index - size + 1 : current_index + 1]
    
    if not window_highs: # Should not happen if size > 0
        return previous_leg

    current_highest = max(window_highs)
    
    new_leg_high = value_at_lag_high > current_highest
    
    # Same for lows
    value_at_lag_low = low[current_index - size]
    window_lows = low[current_index - size + 1 : current_index + 1]
    current_lowest = min(window_lows)
    
    new_leg_low = value_at_lag_low < current_lowest
    
    if new_leg_high:
        return BEARISH_LEG
    elif new_leg_low:
        return BULLISH_LEG
        
    return previous_leg
