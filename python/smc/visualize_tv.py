"""
TradingView Lightweight Charts Visualization.
Generates an HTML file with embedded data and JS logic.
"""

import sys
import os
import json
import random
from datetime import datetime
import webbrowser

# Ensure we can import from local package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from python.smc.constants import *
from python.smc.smc_types import *
from python.smc.functions.get_current_structure import get_current_structure
from python.smc.functions.display_structure import display_structure
from python.smc.visualize import generate_dummy_data # Reuse data gen

def main():
    print("Generating Data...")
    opens, highs, lows, closes, times = generate_dummy_data(300)
    
    # Run SMC Logic (Reuse same logic loop)
    # ... (Copied logic or refactored? I'll copy the loop for simplicity to keep script standalone-ish)
    
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

    # -----------------------------------------------------
    # Prepare Data for Lightweight Charts
    # -----------------------------------------------------
    
    # 1. Candle Data
    candle_data = []
    for j in range(len(times)):
        candle_data.append({
            "time": times[j],
            "open": opens[j],
            "high": highs[j],
            "low": lows[j],
            "close": closes[j]
        })
        
    # 2. Markers (Labels)
    markers = []
    # Identify labels from drawings
    for d in all_drawings:
        if d.get('type') == 'label':
            # {x, y, text, color, style, size}
            # LW Charts Marker: { time, position, color, shape, text }
            
            # Map index 'x' to time
            idx = d.get('x')
            if isinstance(idx, int) and 0 <= idx < len(times):
                m_time = times[idx]
                
                # Determine position and shape
                style = d.get('style', '')
                m_pos = 'aboveBar' if 'down' in style else 'belowBar'
                m_shape = 'arrowDown' if 'down' in style else 'arrowUp'
                
                markers.append({
                    "time": m_time,
                    "position": m_pos,
                    "color": d.get('color', '#000'),
                    "shape": m_shape,
                    "text": d.get('text', '')
                })
                
    # Sort markers by time (required by library)
    markers.sort(key=lambda x: x['time'])
    
    # -----------------------------------------------------
    # HTML Template
    # -----------------------------------------------------
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>SMC TradingView Chart</title>
    <script src="https://unpkg.com/lightweight-charts@4.1.1/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        body {{ margin: 0; padding: 0; background-color: #222; font-family: sans-serif; }}
        #chart {{ width: 100vw; height: 100vh; }}
        #error-log {{ 
            position: absolute; top: 10px; left: 10px; color: red; background: rgba(0,0,0,0.8); 
            padding: 10px; display: none; z-index: 1000; pointer-events: none;
        }}
    </style>
</head>
<body>
    <div id="error-log"></div>
    <div id="chart"></div>
    <script>
        window.onerror = function(msg, url, lineNo, columnNo, error) {{
            const div = document.getElementById('error-log');
            div.style.display = 'block';
            div.innerHTML += 'Error: ' + msg + '<br>';
            return false;
        }};

        if (!window.LightweightCharts) {{
            throw new Error("LightweightCharts library failed to load. Check internet connection.");
        }}

        const chartOptions = {{ 
            layout: {{ 
                textColor: '#d1d4dc', 
                background: {{ type: 'solid', color: '#131722' }} 
            }},
            grid: {{
                vertLines: {{ color: '#363c4e' }},
                horzLines: {{ color: '#363c4e' }}
            }},
            crosshair: {{
                mode: LightweightCharts.CrosshairMode.Normal,
            }},
            timeScale: {{
                borderColor: '#485c7b',
            }},
        }};
        
        try {{
            const container = document.getElementById('chart');
            const chart = LightweightCharts.createChart(container, chartOptions);
            
            const candlestickSeries = chart.addCandlestickSeries({{
                upColor: '#26a69a', downColor: '#ef5350', borderVisible: false, wickUpColor: '#26a69a', wickDownColor: '#ef5350'
            }});
            
            const data = {json.dumps(candle_data)};
            if (!data || data.length === 0) {{
                throw new Error("No data available to render");
            }}
            console.log("Rendering " + data.length + " candles");
            candlestickSeries.setData(data);
            
            const markers = {json.dumps(markers)};
            console.log("Rendering " + markers.length + " markers");
            candlestickSeries.setMarkers(markers);
            
            chart.timeScale().fitContent();
            
            // Handle resize
            window.addEventListener('resize', () => {{
                chart.applyOptions({{ width: window.innerWidth, height: window.innerHeight }});
            }});
            
        }} catch (e) {{
            console.error(e);
            document.getElementById('error-log').style.display = 'block';
            document.getElementById('error-log').innerHTML += 'Render Error: ' + e.message;
        }}
    </script>
</body>
</html>
    """
    
    output_file = "smc_tv_chart.html"
    with open(output_file, "w") as f:
        f.write(html_content)
        
    print(f"Chart saved to {output_file}")
    
    # Auto Open
    try:
        file_path = os.path.abspath(output_file)
        print(f"Opening {file_path} in browser...")
        webbrowser.open('file://' + file_path)
    except Exception as e:
        print(f"Could not open browser automatically: {e}")

if __name__ == "__main__":
    main()
