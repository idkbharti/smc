
import MetaTrader5 as mt5
import pandas as pd

if not mt5.initialize():
    print("MT5 initialization failed", mt5.last_error())
    quit()

symbol = "BCHUSDm"
rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 10)
if rates is None:
    print("Failed to get rates", mt5.last_error())
else:
    print(f"Successfully got {len(rates)} rates for {symbol}")

mt5.shutdown()
