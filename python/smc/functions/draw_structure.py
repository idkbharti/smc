"""
Original Pine Script:
export drawStructure(Pivot p_ivot, string tag, color structureColor, string lineStyle, string labelStyle, string labelSize, string modeInput) =>
    var line l_ine = line.new(na, na, na, na, xloc = xloc.bar_time)
    var label l_abel = label.new(na, na)

    if modeInput == 'Present'
        l_ine.delete()
        l_abel.delete()

    l_ine := line.new(chart.point.new(p_ivot.barTime, na, p_ivot.currentLevel), chart.point.new(time, na, p_ivot.currentLevel), xloc.bar_time, color = structureColor, style = lineStyle)
    l_abel := label.new(chart.point.new(na, math.round(0.5 * (p_ivot.barIndex + bar_index)), p_ivot.currentLevel), tag, xloc.bar_index, color = color(na), textcolor = structureColor, style = labelStyle, size = labelSize)
"""

from typing import Dict, Any, Tuple
from ..smc_types import Pivot

def draw_structure(pivot: Pivot, tag: str, structure_color: str, line_style: str, label_style: str, label_size: str, mode_input: str, current_time: int, current_index: int) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Creates structure line and label.
    
    Args:
        pivot: The pivot point (start of the structure line).
        tag: "BOS" or "CHoCH".
        structure_color: Color of line and text.
        line_style: "solid", "dashed", etc.
        label_style: "label_down", "label_up".
        label_size: "tiny", "small", etc.
        mode_input: "Historical" or "Present".
        current_time: Time of the current bar (end of line).
        current_index: Index of the current bar (used for label positioning).
        
    Returns:
        Tuple containing (Line Object, Label Object).
    """
    
    line_obj = {
        "x1": pivot.barTime,
        "y1": pivot.currentLevel,
        "x2": current_time,
        "y2": pivot.currentLevel,
        "color": structure_color,
        "style": line_style,
        "type": "line"
    }
    
    # Label is positioned halfway between pivot index and current index
    label_index = int(0.5 * (pivot.barIndex + current_index))
    
    label_obj = {
        "x": label_index, # xloc is bar_index
        "y": pivot.currentLevel,
        "text": tag,
        "color": structure_color,
        "style": label_style,
        "size": label_size,
        "type": "label"
    }
    
    return line_obj, label_obj
