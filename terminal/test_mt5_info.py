
import MetaTrader5 as mt5
if not mt5.initialize():
    print("MT5 initialization failed", mt5.last_error())
    quit()

info = mt5.terminal_info()
if info is None:
    print("Failed to get terminal info", mt5.last_error())
else:
    print(f"Connected to broker: {info.connected}")
    print(f"Trade allowed: {info.trade_allowed}")

mt5.shutdown()
