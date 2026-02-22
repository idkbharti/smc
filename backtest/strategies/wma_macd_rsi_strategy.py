from backtest.config import RSI_THRESHOLD, SL_PCT, TP_PCT

# New constants for this strategy specifically
# The user specified 10% in the image.
STRATEGY_SL_PCT = 0.10
STRATEGY_TP_PCT = 0.10

class WmaMacdRsiStrategy:
    def __init__(self):
        self.position = None  # None, 'LONG'
        self.entry_price = 0.0

    def check_entry(self, row, prev_row):
        """
        Checks for ENTRY conditions (LONG ONLY based on request):
        1. WMA(50) > WMA(200)   (Trend)
        2. RSI > 55             (Momentum)
        3. MACD Line crosses above Signal Line
        """
        if self.position is not None:
            return False, None

        # 1. Trend Filter: WMA 50 > WMA 200
        # Check if columns exist
        if 'wma_50' not in row or 'wma_200' not in row:
            return False, None
            
        trend_condition = row['wma_50'] > row['wma_200']
        
        # 2. RSI Condition
        rsi_condition = row['rsi'] > 55
        
        # 3. MACD Crossover
        # Prop: MACD Line (curr) > Signal (curr) AND MACD Line (prev) <= Signal (prev)
        macd_cross_up = (row['macd_line'] > row['signal_line']) and (prev_row['macd_line'] <= prev_row['signal_line'])
        
        if trend_condition and rsi_condition and macd_cross_up:
            return True, 'LONG'
        
        return False, None

    def check_exit(self, row):
        """
        Checks for EXIT conditions (SL or TP)
        """
        if self.position is None:
            return False, None

        # LONG EXIT
        if self.position == 'LONG':
            # Stop Loss
            sl_price = self.entry_price * (1 - STRATEGY_SL_PCT)
            if row['low'] <= sl_price:
                return True, 'SL'

            # Target Profit
            tp_price = self.entry_price * (1 + STRATEGY_TP_PCT)
            if row['high'] >= tp_price:
                return True, 'TP'
                
        # (Short logic can be added here if needed, but request implied Buy)

        return False, None

    def enter_position(self, price, position_type):
        self.position = position_type
        self.entry_price = price

    def exit_position(self):
        self.position = None
        self.entry_price = 0.0
