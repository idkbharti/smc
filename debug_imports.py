try:
    import pandas
    print("pandas imported successfully")
except ImportError as e:
    print(f"Failed to import pandas: {e}")

try:
    import fyers_apiv3
    print("fyers_apiv3 imported successfully")
except ImportError as e:
    print(f"Failed to import fyers_apiv3: {e}")

try:
    import backtest.config
    print("backtest.config imported successfully")
except ImportError as e:
    print(f"Failed to import backtest.config: {e}")
