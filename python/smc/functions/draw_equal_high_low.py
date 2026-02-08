"""
Original Pine Script:
export drawEqualHighLow(Pivot p_ivot, float level, int size, bool equalHigh, Settings settings, EqualDisplay equalDisplay) =>
    string tag = 'EQL'
    color equalColor = settings.swingBullishColor
    string labelStyle = label.style_label_up

    if equalHigh
        tag := 'EQH'
        equalColor := settings.swingBearishColor
        labelStyle := label.style_label_down

    if settings.modeInput == 'Present'
        line.delete(equalDisplay.l_ine)
        label.delete(equalDisplay.l_abel)

    equalDisplay.l_ine := line.new(chart.point.new(p_ivot.barTime, na, p_ivot.currentLevel), chart.point.new(time[size], na, level), xloc = xloc.bar_time, color = equalColor, style = line.style_dotted)
    labelPosition = math.round(0.5 * (p_ivot.barIndex + bar_index - size))
    equalDisplay.l_abel := label.new(chart.point.new(na, labelPosition, level), tag, xloc.bar_index, color = color(na), textcolor = equalColor, style = labelStyle, size = settings.equalHighsLowsSizeInput)
"""

from typing import Dict, Any, List
from ..smc_types import Pivot, Settings, EqualDisplay

def draw_equal_high_low(pivot: Pivot, level: float, size: int, equal_high: bool, settings: Settings, equal_display: EqualDisplay, current_time_minus_size: int, current_index: int) -> EqualDisplay:
    """
    Draws logic for Equal Highs/Lows.
    
    Args:
        pivot: The earlier pivot point.
        level: The current price level matching the pivot.
        size: The offset used (similar to 'size' in leg detection).
        equal_high: True if EQH, False if EQL.
        settings: Settings object.
        equal_display: The display object to update.
        current_time_minus_size: The time at `index - size` (end of the line).
        current_index: The current bar index.
        
    Returns:
        The updated EqualDisplay object.
    """
    
    tag = 'EQL'
    equal_color = settings.swingBullishColor
    label_style = "label_up"
    
    if equal_high:
        tag = 'EQH'
        equal_color = settings.swingBearishColor
        label_style = "label_down"
        
    # In Python we just update the object's fields with the new "drawings"
    
    line_obj = {
        "x1": pivot.barTime,
        "y1": pivot.currentLevel,
        "x2": current_time_minus_size, # time[size]
        "y2": level,
        "color": equal_color,
        "style": "dotted",
        "type": "line"
    }
    
    # Label Position: 0.5 * (pivot_index + (current_index - size))
    # Note: Pine `bar_index` is current. `time[size]` corresponds to `bar_index - size`.
    # labelPosition = math.round(0.5 * (p_ivot.barIndex + bar_index - size))
    label_pos_index = int(0.5 * (pivot.barIndex + current_index - size))
    
    label_obj = {
        "x": label_pos_index,
        "y": level,
        "text": tag,
        "color": equal_color,
        "style": label_style,
        "size": settings.equalHighsLowsSizeInput,
        "type": "label"
    }
    
    equal_display.l_ine = line_obj
    equal_display.l_abel = label_obj
    
    return equal_display
