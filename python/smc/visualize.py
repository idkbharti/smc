"""
Visualization Script for SMC Python Library.
Uses Plotly to render the chart and overlays.
"""

import sys
import os
import random
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import webbrowser
import os

# Ensure we can import from local package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from python.smc.constants import *
from python.smc.smc_types import *
from python.smc.functions.get_current_structure import get_current_structure
from python.smc.functions.display_structure import display_structure

def generate_dummy_data(length=200):
    highs = []
    lows = []
    opens = []
    closes = []
    times = []
    
    # Start time roughly now backdated
    start_ts = 1672531200 # 2023-01-01
    
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
        times.append(start_ts + i * 3600) # Hourly
        
        price = close_p
        
    return opens, highs, lows, closes, times

def map_style(style_str):
    if style_str == 'dashed': return 'dash'
    if style_str == 'dotted': return 'dot'
    return 'solid'

def main():
    print("Generating Data...")
    opens, highs, lows, closes, times = generate_dummy_data(300)
    
    # Convert timestamps to datetime for Plotly
    dates = [datetime.fromtimestamp(t) for t in times]
    
    print("Running SMC Logic...")
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
    
    swing_trend = Trend()
    internal_trend = Trend()
    
    equal_high_display = EqualDisplay()
    equal_low_display = EqualDisplay()
    
    swing_obs = []
    internal_obs = []
    
    swing_leg_direction = 0
    internal_leg_direction = 0
    atr = 1.0 
    
    all_drawings = []
    
    for i in range(50, len(times)):
        # 1. Swing
        res_swing = get_current_structure(
            size=10, equal_high_low=False, internal=False, settings=settings, alerts=alerts, 
            trailing=trailing, internal_low=internal_low, internal_high=internal_high, 
            swing_low=swing_low, swing_high=swing_high, equal_low=equal_low, equal_high=equal_high, 
            atr_measure=atr, equal_low_display=equal_low_display, equal_high_display=equal_high_display,
            high=highs, low=lows, times=times, current_index=i, previous_leg_direction=swing_leg_direction
        )
        swing_leg_direction = res_swing["new_leg_direction"]
        all_drawings.extend(res_swing["drawings"])
        
        # 2. Internal
        res_internal = get_current_structure(
            size=5, equal_high_low=False, internal=True, settings=settings, alerts=alerts, 
            trailing=trailing, internal_low=internal_low, internal_high=internal_high, 
            swing_low=swing_low, swing_high=swing_high, equal_low=equal_low, equal_high=equal_high, 
            atr_measure=atr, equal_low_display=equal_low_display, equal_high_display=equal_high_display,
            high=highs, low=lows, times=times, current_index=i, previous_leg_direction=internal_leg_direction
        )
        internal_leg_direction = res_internal["new_leg_direction"]
        all_drawings.extend(res_internal["drawings"])
        
        # 3. Structure
        d_int = display_structure(
            internal=True, settings=settings, alerts=alerts,
            internal_high=internal_high, swing_high=swing_high, internal_low=internal_low, swing_low=swing_low,
            internal_trend=internal_trend, swing_trend=swing_trend,
            internal_order_blocks=internal_obs, swing_order_blocks=swing_obs,
            parsed_highs=highs, parsed_lows=lows, times=times,
            current_high=highs[i], current_low=lows[i], current_close=closes[i], current_open=opens[i],
            current_time=times[i], current_index=i
        )
        all_drawings.extend(d_int)
        
        d_swing = display_structure(
            internal=False, settings=settings, alerts=alerts,
            internal_high=internal_high, swing_high=swing_high, internal_low=internal_low, swing_low=swing_low,
            internal_trend=internal_trend, swing_trend=swing_trend,
            internal_order_blocks=internal_obs, swing_order_blocks=swing_obs,
            parsed_highs=highs, parsed_lows=lows, times=times,
            current_high=highs[i], current_low=lows[i], current_close=closes[i], current_open=opens[i],
            current_time=times[i], current_index=i
        )
        all_drawings.extend(d_swing)

    print(f"Total Drawings: {len(all_drawings)}")
    
    print("Creating Plotly Chart...")
    fig = go.Figure(data=[go.Candlestick(x=dates,
                open=opens, high=highs, low=lows, close=closes)])

    # Helper map for indices to dates
    def get_date(idx_or_ts):
        # If it's a timestamp (large int), convert directly
        if idx_or_ts > 1000000000:
            return datetime.fromtimestamp(idx_or_ts)
        # If it's an index (small int), lookup in times
        if isinstance(idx_or_ts, int) and 0 <= idx_or_ts < len(times):
            return datetime.fromtimestamp(times[idx_or_ts])
        return None

    for d in all_drawings:
        try:
            if d.get('type') == 'line':
                # {x1, y1, x2, y2, color, style}
                x0 = get_date(d['x1'])
                x1 = get_date(d['x2'])
                if x0 and x1:
                    fig.add_shape(type="line",
                        x0=x0, y0=d['y1'], x1=x1, y1=d['y2'],
                        line=dict(color=d['color'], width=2, dash=map_style(d.get('style', 'solid')))
                    )
            elif d.get('type') == 'label':
                # {x, y, text, color, style, size}
                # x is index usually? My code returns index for labels in `draw_structure`.
                x_val = get_date(d['x'])
                if x_val:
                    # Adjust yshift based on style
                    yshift = 15 if 'down' in d.get('style', '') else -15
                    fig.add_annotation(
                        x=x_val, y=d['y'],
                        text=d.get('text', ''),
                        showarrow=False,
                        yshift=yshift,
                        font=dict(color=d.get('color', 'black'), size=10)
                    )
            elif d.get('type') == 'box':
                # {left, top, right, bottom, bg_color, border_color}
                x0 = get_date(d['left'])
                x1 = get_date(d['right'])
                if x0 and x1:
                    fig.add_shape(type="rect",
                        x0=x0, y0=d['top'], x1=x1, y1=d['bottom'],
                        line=dict(color=d.get('border_color', 'black')),
                        fillcolor=d.get('bg_color', 'grey'),
                        opacity=0.3
                    )
        except Exception as e:
            print(f"Error drawing item: {d} -> {e}")

    fig.update_layout(title='SMC Python Visualization', xaxis_rangeslider_visible=False)
    
    output_file = "smc_chart.html"
    fig.write_html(output_file)
    print(f"Chart saved to {output_file}")
    
    # Automatically open the chart
    try:
        file_path = os.path.abspath(output_file)
        print(f"Opening {file_path} in browser...")
        webbrowser.open('file://' + file_path)
    except Exception as e:
        print(f"Could not open browser automatically: {e}")

if __name__ == "__main__":
    main()
