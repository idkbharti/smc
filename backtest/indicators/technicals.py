import pandas as pd
import numpy as np

def calculate_rsi(df, period=14):
    """
    Calculates RSI (Relative Strength Index).
    """
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # Smoothing (Wilder's Smoothing) - optional but more standard
    # This simple rolling mean is often sufficient for basic backtests but let's do Wilder's if we can request it. 
    # For now utilizing simple rolling for stability unless requested otherwise.
    # Actually, let's implement the standard Wilder's smoothing for RSI as it's more accurate.
    
    delta = df['close'].diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    
    ma_up = up.ewm(com=period - 1, adjust=True, min_periods=period).mean()
    ma_down = down.ewm(com=period - 1, adjust=True, min_periods=period).mean()
    
    rs = ma_up / ma_down
    df['rsi'] = 100 - (100 / (1 + rs))
    
    return df

def calculate_adx(df, period=14):
    """
    Calculates ADX (Average Directional Index).
    """
    df['up_move'] = df['high'] - df['high'].shift(1)
    df['down_move'] = df['low'].shift(1) - df['low']
    
    df['plus_dm'] = np.where((df['up_move'] > df['down_move']) & (df['up_move'] > 0), df['up_move'], 0)
    df['minus_dm'] = np.where((df['down_move'] > df['up_move']) & (df['down_move'] > 0), df['down_move'], 0)
    
    df['tr1'] = df['high'] - df['low']
    df['tr2'] = abs(df['high'] - df['close'].shift(1))
    df['tr3'] = abs(df['low'] - df['close'].shift(1))
    df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
    
    # Smoothing
    df['atr'] = df['tr'].rolling(window=period).mean() # Simple moving average for ATR in ADX usually? Or Wilder's?
    # Wilder's smoothing for ADX components
    
    alpha = 1/period
    
    # We need to use ewm for Wilder's smoothing equivalent
    df['atr'] = df['tr'].ewm(alpha=alpha, adjust=False).mean()
    df['plus_di'] = 100 * (df['plus_dm'].ewm(alpha=alpha, adjust=False).mean() / df['atr'])
    df['minus_di'] = 100 * (df['minus_dm'].ewm(alpha=alpha, adjust=False).mean() / df['atr'])
    
    df['dx'] = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])
    df['adx'] = df['dx'].ewm(alpha=alpha, adjust=False).mean()
    
    return df

def calculate_ema(df, period=200):
    """
    Calculates Exponential Moving Average (EMA).
    """
    df[f'ema_{period}'] = df['close'].ewm(span=period, adjust=False).mean()
    return df

def calculate_wma(df, period=50):
    """
    Calculates Weighted Moving Average (WMA).
    weights = [1, 2, ..., n]
    """
    weights = np.arange(1, period + 1)
    
    def wma_calc(x):
        return np.dot(x, weights) / weights.sum()
        
    df[f'wma_{period}'] = df['close'].rolling(window=period).apply(wma_calc, raw=True)
    return df

def calculate_macd(df, fast=12, slow=26, signal=9):
    """
    Calculates MACD (Moving Average Convergence Divergence).
    """
    exp1 = df['close'].ewm(span=fast, adjust=False).mean()
    exp2 = df['close'].ewm(span=slow, adjust=False).mean()
    
    df['macd_line'] = exp1 - exp2
    df['signal_line'] = df['macd_line'].ewm(span=signal, adjust=False).mean()
    df['macd_hist'] = df['macd_line'] - df['signal_line']
    
    return df
