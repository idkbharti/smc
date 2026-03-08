import pandas as pd
import numpy as np
import MetaTrader5 as mt5
from datetime import datetime, timedelta
import os

def generate_data(rows: int = 2000, start_price: float = 1.10) -> pd.DataFrame:
    np.random.seed(99)
    # Use the provided starting price
    closes = np.cumprod(1 + np.random.normal(0, 0.0018, rows)) * start_price
    start  = datetime(2025, 1, 1)
    out    = []
    for i in range(rows):
        t = start + timedelta(minutes=15 * i)
        c = closes[i]
        o = closes[i-1] if i > 0 else c
        h = max(o, c) + abs(np.random.normal(0, c * 0.0006))
        l = min(o, c) - abs(np.random.normal(0, c * 0.0006))
        out.append({
            'time': t, 
            'open': float(round(o, 5)), 
            'high': float(round(h, 5)),
            'low': float(round(l, 5)), 
            'close': float(round(c, 5))
        })
    return pd.DataFrame(out)

def fetch_mt5_data(symbol="EURUSD", timeframe=mt5.TIMEFRAME_M15, bars=2000):
    if not mt5.initialize():
        # Fallback to synthetic if MT5 not available
        return generate_data(bars)
        
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
    if rates is None:
        return generate_data(bars)
        
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    # Filter columns
    return df[['time', 'open', 'high', 'low', 'close']]

class DataFeed:
    # Legacy class for other potential imports
    def __init__(self, mode="live"):
        self.mode = mode
    
    def get_initial_history(self, symbol, tf, count=2000):
        return fetch_mt5_data(symbol, tf, count)
