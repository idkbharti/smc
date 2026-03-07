import pandas as pd
import os

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    print("MetaTrader5 library not found. Running in Offline CSV Mode.")

class DataFeed:
    def __init__(self, mode="offline", csv_path=None):
        self.mode = mode
        self.csv_path = csv_path
        self._historical_data = None
        self._current_index = 0
        
        if self.mode == "live" and not MT5_AVAILABLE:
            raise RuntimeError("Live mode requested but MetaTrader5 library is not installed.")
            
        if self.mode == "offline":
            self._load_csv()
            
    def _load_csv(self):
        if not self.csv_path or not os.path.exists(self.csv_path):
            raise FileNotFoundError(f"CSV not found: {self.csv_path}")
            
        self._historical_data = pd.read_csv(self.csv_path)
        # Ensure correct column names
        self._historical_data.columns = [c.lower() for c in self._historical_data.columns]
        
    def get_initial_history(self, num_bars=500):
        """
        Returns the first block of bars to 'prime' the chart.
        """
        if self.mode == "offline":
            self._current_index = num_bars
            return self._historical_data.iloc[:num_bars].copy()
        else:
            # LIVE MT5 Implementation
            pass
            
    def get_next_bar(self):
        """
        Bar Replay: Yields exactly one new candle.
        """
        if self.mode == "offline":
            if self._current_index < len(self._historical_data):
                bar = self._historical_data.iloc[self._current_index:self._current_index+1].copy()
                self._current_index += 1
                return bar
            return None # End of data
        else:
            # LIVE MT5 Implementation
            pass
