"""
Original Pine Script:
export drawZone(float labelLevel, int labelIndex, float top, float bottom, string tag, color zoneColor, string style, int barTime) =>
    var label l_abel = label.new(na, na, text = tag, color = color(na), textcolor = zoneColor, style = style, size = size.small)
    var box b_ox = box.new(na, na, na, na, bgcolor = color.new(zoneColor, 80), border_color = color(na), xloc = xloc.bar_time)
    b_ox.set_top_left_point(chart.point.new(barTime, na, top))
    b_ox.set_bottom_right_point(chart.point.new(time, na, bottom))
    l_abel.set_point(chart.point.new(na, labelIndex, labelLevel))
"""

from typing import Dict, Any

def draw_zone(label_level: float, label_index: int, top: float, bottom: float, tag: str, zone_color: str, style: str, bar_time: int, current_time: int) -> Dict[str, Any]:
    """
    Draws a zone (box) and a label.
    
    Args:
        label_level: Price level for the label.
        label_index: Bar index for the label.
        top: Top price of the zone.
        bottom: Bottom price of the zone.
        tag: Text for the label.
        zone_color: Color of zone and text.
        style: Label style.
        bar_time: Start time of the zone.
        current_time: End time of the zone (current bar).
        
    Returns:
        Dictionary containing 'box' and 'label' objects.
    """
    
    box_obj = {
        "left": bar_time,
        "top": top,
        "right": current_time,
        "bottom": bottom,
        "bg_color": zone_color, # with transparency usually
        "border_color": "NA",
        "type": "box"
    }
    
    label_obj = {
        "x": label_index, # xloc is bar_index
        "y": label_level,
        "text": tag,
        "color": zone_color,
        "style": style,
        "size": "small",
        "type": "label"
    }
    
    return {"box": box_obj, "label": label_obj}
