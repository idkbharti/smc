import fastapi
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import pandas as pd
import numpy as np
import MetaTrader5 as mt5
from typing import Dict, List, Optional
from datetime import datetime
from contextlib import asynccontextmanager
import json

# Import the extracted engine
from smc_engine_v2 import SMCEngine, BULLISH, BEARISH
from data_feed import fetch_mt5_data
import numpy as np

def to_seconds(val):
    if val is None: return None
    try:
        # Handle datetime objects
        if hasattr(val, 'timestamp'):
            return int(val.timestamp())
        # Handle pandas/numpy timestamps
        if isinstance(val, (np.datetime64, pd.Timestamp)):
            return int(pd.to_datetime(val).timestamp())
        # Handle strings
        if isinstance(val, str):
            return int(pd.to_datetime(val).timestamp())
        # Handle numbers (assume seconds if small, nanoseconds if huge)
        num = int(val)
        if num > 10**11: # Likely nanoseconds or milliseconds
            return int(pd.to_datetime(num).timestamp())
        return num
    except:
        return None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize MT5
    if not mt5.initialize():
        print("MT5 initialization failed: ", mt5.last_error())
    else:
        print("MT5 connected for API")
    yield
    # Shutdown: Clean up
    mt5.shutdown()
    print("MT5 connection closed")

app = FastAPI(title="SMC Terminal API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/init")
async def get_init():
    if not mt5.initialize():
        return {
            "status": "error", 
            "message": f"MT5 not connected. Error: {mt5.last_error()}",
            "account": None,
            "watchlist": ["BTCUSDm", "EURUSDm", "XAUUSDm"]
        }
    
    acc = mt5.account_info()
    symbols = mt5.symbols_get()
    watchlist = []
    if symbols:
        watchlist = [s.name for s in symbols if s.visible]
        if not watchlist:
            watchlist = [s.name for s in symbols[:50]]

    return {
        "account": {
            "name": str(getattr(acc, "name", "N/A")),
            "server": str(getattr(acc, "server", "N/A")),
            "balance": float(getattr(acc, "balance", 0.0)),
            "equity": float(getattr(acc, "equity", 0.0)),
            "currency": str(getattr(acc, "currency", "USD")),
            "trade_mode": int(getattr(acc, "trade_mode", 0)), 
        },
        "watchlist": watchlist
    }

@app.get("/api/history")
async def get_history(symbol: str = "EURUSD", timeframe: int = 15, count: int = 2000):
    tf_map = {1: mt5.TIMEFRAME_M1, 5: mt5.TIMEFRAME_M5, 15: mt5.TIMEFRAME_M15, 60: mt5.TIMEFRAME_H1, 240: mt5.TIMEFRAME_H4}
    mt5_tf = tf_map.get(timeframe, mt5.TIMEFRAME_M15)
    
    df = fetch_mt5_data(symbol, mt5_tf, count)
    if df.empty:
        # Smart synthetic fallback
        start_px = 1.10
        s_upper = symbol.upper()
        if "BTC" in s_upper: start_px = 65000.0
        elif "ETH" in s_upper: start_px = 2500.0
        elif "BCH" in s_upper: start_px = 520.0
        elif "XAU" in s_upper or "GOLD" in s_upper: start_px = 2300.0
        
        from data_feed import generate_data
        df = generate_data(count, start_price=start_px)
    
    candles = []
    for _, row in df.iterrows():
        candles.append({
            "time": to_seconds(row['time']),
            "open": float(row['open']),
            "high": float(row['high']),
            "low": float(row['low']),
            "close": float(row['close'])
        })
    return {"candles": candles}

@app.post("/api/engine/analyze")
async def analyze_data(payload: Dict):
    symbol = payload.get("symbol", "EURUSD")
    tf = payload.get("timeframe", 15)
    current_idx = payload.get("currentIndex", 200)
    rr = payload.get("rr", 3.0)

    tf_map = {1: mt5.TIMEFRAME_M1, 5: mt5.TIMEFRAME_M5, 15: mt5.TIMEFRAME_M15, 60: mt5.TIMEFRAME_H1, 240: mt5.TIMEFRAME_H4}
    mt5_tf = tf_map.get(tf, mt5.TIMEFRAME_M15)

    # Estimate a starting price for synthetic fallback based on common symbols
    # EURUSD ~1.1, BTC ~60k, ETH ~2500, BCH ~500, Gold ~2000
    start_px = 1.10
    s_upper = symbol.upper()
    if "BTC" in s_upper: start_px = 65000.0
    elif "ETH" in s_upper: start_px = 2500.0
    elif "BCH" in s_upper: start_px = 520.0
    elif "XAU" in s_upper or "GOLD" in s_upper: start_px = 2300.0
    elif "USD" in s_upper: start_px = 1.10

    df = fetch_mt5_data(symbol, mt5_tf, 2000)
    if df.empty:
        # If fetch fails, try to get at least something that isn't hardcoded to EURUSD price
        from data_feed import generate_data
        df = generate_data(2000, start_price=start_px)

    # The engine needs a rolling window or the full history up to now to detect structure
    length = payload.get("length", 20)
    
    # Slice data to the current "visible" range (for bar replay support)
    visible_df = df.iloc[:current_idx] if current_idx < len(df) else df
    
    # Run engine (matches "stable" config with length=20 by default)
    engine = SMCEngine(length=length, rr=rr) 
    engine.update(visible_df)

    obs_data = []
    for ob in engine.obs:
        obs_data.append({
            "time": to_seconds(ob.time),
            "high": float(ob.high),
            "low": float(ob.low),
            "bias": "bullish" if ob.bias == BULLISH else "bearish",
            "partial": bool(ob.partial),
            "cur_h": float(ob.cur_h),
            "cur_l": float(ob.cur_l),
            "mitigated": bool(ob.mitigated),
            "is_refined": bool(ob.is_refined)
        })

    struc_data = []
    for ev in engine.structure:
        struc_data.append({
            "time": to_seconds(ev.time),
            "level": float(ev.level),
            "kind": str(ev.kind),
            "direction": "bullish" if ev.direction == BULLISH else "bearish"
        })

    processed_trades = []
    for tr in engine.trades:
        processed_trades.append({
            "time": to_seconds(tr['time']),
            "dir": str(tr['dir']),
            "entry": float(tr['entry']),
            "sl": float(tr['sl']),
            "tp": float(tr['tp']),
            "result": str(tr['result'])
        })

    return {
        "status": "success",
        "trend": "bullish" if engine.trend == BULLISH else "bearish" if engine.trend == BEARISH else "neutral",
        "obs": obs_data,
        "structure": struc_data,
        "trades": processed_trades,
        "trails": {
            "top": float(engine.trail_top) if engine.trail_top is not None else None,
            "top_time": to_seconds(engine.trail_top_time),
            "bottom": float(engine.trail_bottom) if engine.trail_bottom is not None else None,
            "bottom_time": to_seconds(engine.trail_bot_time),
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8085)
