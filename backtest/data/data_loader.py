"""
Data loaders for fetching historical OHLCV data.

Sources:
  - yfinance: Gold (GC=F), Silver (SI=F), BTC (BTC-USD)
    • 5m/15m: last 60 days only
    • 1H: last 730 days
  - ccxt + Binance: BTC/USDT with years of history for all timeframes
  - CSV: any exported data
"""

import pandas as pd
import os
from typing import Optional


# ─── yfinance Loader ─────────────────────────────────────────────────────────

def load_yfinance(symbol: str, interval: str = '15m',
                  period: str = '60d') -> pd.DataFrame:
    """
    Fetch historical data from Yahoo Finance.

    Args:
        symbol:   Ticker (e.g. 'GC=F' for Gold, 'SI=F' for Silver, 'BTC-USD')
        interval: '5m', '15m', '1h', '1d'
        period:   '60d' for intraday, '730d' or '2y' for hourly+

    Returns:
        DataFrame with columns: date, open, high, low, close, volume
    """
    try:
        import yfinance as yf
    except ImportError:
        raise ImportError("yfinance not installed. Run: pip install yfinance")

    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval)

    if df.empty:
        print(f"[WARN] No data returned for {symbol} {interval} {period}")
        return pd.DataFrame()

    df = df.reset_index()

    # Normalise column names
    col_map = {}
    for col in df.columns:
        lc = col.lower()
        if lc in ('date', 'datetime'):
            col_map[col] = 'date'
        elif lc == 'open':
            col_map[col] = 'open'
        elif lc == 'high':
            col_map[col] = 'high'
        elif lc == 'low':
            col_map[col] = 'low'
        elif lc == 'close':
            col_map[col] = 'close'
        elif lc == 'volume':
            col_map[col] = 'volume'
    df = df.rename(columns=col_map)

    # Keep only the columns we need
    required = ['date', 'open', 'high', 'low', 'close', 'volume']
    for col in required:
        if col not in df.columns:
            if col == 'volume':
                df['volume'] = 0
            elif col == 'date':
                df['date'] = df.index
            else:
                raise ValueError(f"Missing required column: {col}")

    df = df[required].copy()
    df = df.dropna(subset=['open', 'high', 'low', 'close'])
    df = df.reset_index(drop=True)

    print(f"[yfinance] Loaded {len(df)} bars for {symbol} {interval}")
    return df


# ─── ccxt / Binance Loader ───────────────────────────────────────────────────

def load_ccxt(symbol: str = 'BTC/USDT', timeframe: str = '15m',
              since_days: int = 365, exchange_id: str = 'binance') -> pd.DataFrame:
    """
    Fetch historical OHLCV data from a crypto exchange via ccxt.

    Args:
        symbol:      Trading pair (e.g. 'BTC/USDT')
        timeframe:   '5m', '15m', '1h', '4h', '1d'
        since_days:  How many days of history to fetch
        exchange_id: Exchange name (default: 'binance')

    Returns:
        DataFrame with columns: date, open, high, low, close, volume
    """
    try:
        import ccxt
    except ImportError:
        raise ImportError("ccxt not installed. Run: pip install ccxt")

    import datetime

    exchange_class = getattr(ccxt, exchange_id)
    exchange = exchange_class({'enableRateLimit': True})

    since = exchange.parse8601(
        (datetime.datetime.utcnow() - datetime.timedelta(days=since_days)).isoformat()
    )

    all_data = []
    limit = 1000  # Max candles per request

    while True:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
        if not ohlcv:
            break
        all_data.extend(ohlcv)
        since = ohlcv[-1][0] + 1  # Next ms after last candle
        if len(ohlcv) < limit:
            break

    if not all_data:
        print(f"[WARN] No data returned for {symbol} {timeframe}")
        return pd.DataFrame()

    df = pd.DataFrame(all_data, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
    df['date'] = pd.to_datetime(df['date'], unit='ms')
    df = df.drop_duplicates(subset='date')
    df = df.sort_values('date').reset_index(drop=True)

    print(f"[ccxt] Loaded {len(df)} bars for {symbol} {timeframe} ({since_days}d)")
    return df


# ─── CSV Loader ──────────────────────────────────────────────────────────────

def load_csv(filepath: str) -> pd.DataFrame:
    """
    Load OHLCV data from a CSV file.

    Expects columns: date, open, high, low, close, volume
    (column names are case-insensitive)
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"CSV file not found: {filepath}")

    df = pd.read_csv(filepath)

    # Normalise column names to lowercase
    df.columns = [c.lower().strip() for c in df.columns]

    # Rename common variants
    rename = {}
    for col in df.columns:
        if col in ('datetime', 'timestamp', 'time'):
            rename[col] = 'date'
    df = df.rename(columns=rename)

    required = ['date', 'open', 'high', 'low', 'close']
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}. Found: {list(df.columns)}")

    if 'volume' not in df.columns:
        df['volume'] = 0

    df['date'] = pd.to_datetime(df['date'])
    df = df[['date', 'open', 'high', 'low', 'close', 'volume']].copy()
    df = df.dropna(subset=['open', 'high', 'low', 'close'])
    df = df.sort_values('date').reset_index(drop=True)

    print(f"[CSV] Loaded {len(df)} bars from {filepath}")
    return df


# ─── Convenience Mapping ─────────────────────────────────────────────────────

SYMBOLS = {
    'gold': {'yfinance': 'GC=F', 'name': 'Gold Futures'},
    'silver': {'yfinance': 'SI=F', 'name': 'Silver Futures'},
    'btc': {'yfinance': 'BTC-USD', 'ccxt': 'BTC/USDT', 'name': 'Bitcoin'},
}

TIMEFRAMES = {
    '5m':  {'yfinance': '5m',  'ccxt': '5m',  'period': '60d',   'label': '5 Minute'},
    '15m': {'yfinance': '15m', 'ccxt': '15m', 'period': '60d',   'label': '15 Minute'},
    '1h':  {'yfinance': '1h',  'ccxt': '1h',  'period': '730d',  'label': '1 Hour'},
    '1d':  {'yfinance': '1d',  'ccxt': '1d',  'period': '5y',    'label': '1 Day'},
}


def load_data(asset: str, timeframe: str, source: str = 'auto',
              csv_path: Optional[str] = None) -> pd.DataFrame:
    """
    High-level loader. Picks the best source based on asset and timeframe.

    Args:
        asset:     'gold', 'silver', or 'btc'
        timeframe: '5m', '15m', or '1h'
        source:    'yfinance', 'ccxt', 'csv', or 'auto'
        csv_path:  Path to CSV file (required if source='csv')
    """
    asset = asset.lower()
    timeframe = timeframe.lower()

    if source == 'csv':
        if not csv_path:
            raise ValueError("csv_path required when source='csv'")
        return load_csv(csv_path)

    sym_info = SYMBOLS.get(asset)
    tf_info = TIMEFRAMES.get(timeframe)

    if not sym_info:
        raise ValueError(f"Unknown asset: {asset}. Choose from: {list(SYMBOLS.keys())}")
    if not tf_info:
        raise ValueError(f"Unknown timeframe: {timeframe}. Choose from: {list(TIMEFRAMES.keys())}")

    if source == 'auto':
        source = 'yfinance'

    if source == 'ccxt':
        ccxt_sym = sym_info.get('ccxt')
        if not ccxt_sym:
            raise ValueError(f"ccxt not available for {asset}. Use yfinance.")
        if timeframe in ('1h', '1d'):
            days = 730
        else:
            days = 60
        return load_ccxt(symbol=ccxt_sym, timeframe=tf_info['ccxt'], since_days=days)

    else:  # yfinance
        return load_yfinance(
            symbol=sym_info['yfinance'],
            interval=tf_info['yfinance'],
            period=tf_info['period']
        )
