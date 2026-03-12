import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from smc_engine_v2 import SMCEngine, BULLISH, BEARISH

def generate_test_data(rows=400):
    np.random.seed(42)
    closes = np.cumprod(1 + np.random.normal(0, 0.002, rows)) * 60000
    start = datetime(2025, 1, 1)
    out = []
    for i in range(rows):
        t = start + timedelta(minutes=i)
        c = closes[i]
        o = closes[i-1] if i > 0 else c
        h = max(o, c) + abs(np.random.normal(0, 10))
        l = min(o, c) - abs(np.random.normal(0, 10))
        out.append({'time': t, 'open': o, 'high': h, 'low': l, 'close': c})
    return pd.DataFrame(out)

df = generate_test_data(400)
engine = SMCEngine(length=20) # Use smaller length for easier detection
engine.update(df)

print(f"Bars: {len(df)}")
print(f"Trend: {engine.trend}")
print(f"OBs found: {len(engine.obs)}")
print(f"Structure events: {len(engine.structure)}")
print(f"Trail Top: {engine.trail_top} at {engine.trail_top_time}")
print(f"Trail Bottom: {engine.trail_bottom} at {engine.trail_bot_time}")

for ob in engine.obs[:5]:
    print(f"  OB: {ob.time} {ob.bias} {'Refined' if ob.is_refined else ''}")

for ev in engine.structure[:5]:
    print(f"  Structure: {ev.kind} {ev.level} {ev.time}")
