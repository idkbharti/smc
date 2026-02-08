"""
Original Pine Script:
export fairValueGapBox(int leftTime, int rightTime, float topPrice, float bottomPrice, color boxColor, int extendInput) =>
    box.new(chart.point.new(leftTime, na, topPrice), chart.point.new(rightTime + extendInput * (time - time[1]), na, bottomPrice), xloc = xloc.bar_time, border_color = boxColor, bgcolor = boxColor)
"""

from typing import Dict, Any

def fair_value_gap_box(left_time: int, right_time: int, top_price: float, bottom_price: float, box_color: str, extend_input: int, time_delta: int) -> Dict[str, Any]:
    """
    Creates a box for FVG.
    
    Args:
        left_time: Start time of FVG.
        right_time: End time (usually current bar time).
        top_price: Upper price of FVG.
        bottom_price: Lower price of FVG.
        box_color: Color string.
        extend_input: Number of bars to extend.
        time_delta: Duration of one bar (time - time[1]).
        
    Returns:
        Box object dictionary.
    """
    
    extended_right_time = right_time + (extend_input * time_delta)
    
    box_obj = {
        "left": left_time,
        "top": top_price,
        "right": extended_right_time,
        "bottom": bottom_price,
        "color": box_color,
        "bg_color": box_color, # usually same as border in this script
        "type": "box"
    }
    return box_obj
