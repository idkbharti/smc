import pandas as pd
from fyers_apiv3 import fyersModel
import datetime
import time

def fetch_historical_data(client_id, access_token, symbol, timeframe="15", duration_days=730):
    """
    Fetches historical data from Fyers API.
    
    Args:
        client_id (str): Fyers Client ID
        access_token (str): Fyers Access Token
        symbol (str): Symbol to fetch (e.g., "NSE:RELIANCE-EQ")
        timeframe (str): Timeframe in minutes (e.g., "15"). Fyers uses "15" for 15m.
        duration_days (int): Number of days of data to fetch.
        
    Returns:
        pd.DataFrame: DataFrame with date, open, high, low, close, volume
    """
    
    # Initialize Fyers Model
    fyers = fyersModel.FyersModel(client_id=client_id, token=access_token, log_path="")
    
    # Calculate Date Range
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=duration_days)
    
    # Format dates as YYYY-MM-DD
    range_from = start_date.strftime("%Y-%m-%d")
    range_to = end_date.strftime("%Y-%m-%d")
    
    # Fyers History Data Parameters
    data = {
        "symbol": symbol,
        "resolution": timeframe,
        "date_format": "1",
        "range_from": range_from,
        "range_to": range_to
    }
    
    # Debug: Print the request range
    # print(f"DEBUG: Fetching {symbol} {timeframe} from {range_from} to {range_to}")
    try:
        with open("loader_debug.txt", "a") as f:
            f.write(f"Requesting {symbol}: {range_from} to {range_to} (Res: {timeframe})\n")
    except:
        pass
    
    try:
        response = fyers.history(data=data)
        
        if response['s'] == 'ok':
            candles = response['candles']
            df = pd.DataFrame(candles, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
            
            # Convert timestamp to datetime
            df['date'] = pd.to_datetime(df['date'], unit='s')
            df['date'] = df['date'].dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
            
            return df
        else:
            # Raise exception with the error message from Fyers
            raise Exception(f"Fyers API Error: {response['message']}")
            
    except Exception as e:
        # Re-raise the exception to be caught by main.py
        raise e

if __name__ == "__main__":
    # Test stub
    pass
