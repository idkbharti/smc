"""
Original Pine Script:
export drawLabel(int labelTime, float labelPrice, string tag, color labelColor, string labelStyle, string modeInput) =>
    var label l_abel = na
    if modeInput == 'Present'
        l_abel.delete()
    l_abel := label.new(chart.point.new(labelTime, na, labelPrice), tag, xloc.bar_time, color = color(na), textcolor = labelColor, style = labelStyle, size = size.small)
"""

from typing import Optional, Dict, Any

def draw_label(label_time: int, label_price: float, tag: str, label_color: str, label_style: str, mode_input: str) -> Dict[str, Any]:
    """
    Creates a label object (simulated).
    
    Args:
        label_time: The timestamp for the label.
        label_price: The price level for the label.
        tag: The text to display.
        label_color: Color of the text (e.g., hex string).
        label_style: Style of the label (e.g., "label_up", "label_down").
        mode_input: "Historical" or "Present".
        
    Returns:
        A dictionary representing the created label.
    """
    # Logic:
    # If mode is 'Present', we would normally delete the old label.
    # In a backtesting/static context, we just return the new label definition.
    
    label_obj = {
        "x": label_time,
        "y": label_price,
        "text": tag,
        "color": label_color,
        "style": label_style,
        "size": "small",
        "action": "create"
    }
    
    if mode_input == 'Present':
        label_obj["action"] = "update_last" 
        # Implies we track the last one and update it, but here we just return the spec.
        
    return label_obj
