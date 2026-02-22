from backtest.config import ADX_THRESHOLD, RSI_THRESHOLD, SL_PCT, TP_PCT

class AdxRsiStrategy:
    def __init__(self):
        self.position = None  # None, 'LONG', 'SHORT'
        self.entry_price = 0.0

    def check_entry(self, row, prev_row):
        """
        Checks for entry conditions:
        LONG:
        1. Close > EMA 200
        2. ADX > 25
        3. DI+ > DI-
        4. RSI > 55
        
        SHORT:
        1. Close < EMA 200
        2. ADX > 25
        3. DI- > DI+
        4. RSI < 45
        """
        if self.position is not None:
            return False, None

        # Common conditions
        adx_condition = row['adx'] > ADX_THRESHOLD
        
        # Long Conditions
        long_trend = row['close'] > row['ema_200']
        long_directional = row['plus_di'] > row['minus_di']
        long_rsi = row['rsi'] > 55
        
        if long_trend and adx_condition and long_directional and long_rsi:
            return True, 'LONG'
            
        # Short Conditions
        short_trend = row['close'] < row['ema_200']
        short_directional = row['minus_di'] > row['plus_di']
        short_rsi = row['rsi'] < 45
        
        if short_trend and adx_condition and short_directional and short_rsi:
            return True, 'SHORT'
        
        return False, None

    def check_exit(self, row):
        """
        Checks for exit conditions (SL or TP)
        """
        if self.position is None:
            return False, None

        # LONG EXIT
        if self.position == 'LONG':
            # Stop Loss
            sl_price = self.entry_price * (1 - SL_PCT)
            if row['low'] <= sl_price:
                return True, 'SL'

            # Target Profit
            tp_price = self.entry_price * (1 + TP_PCT)
            if row['high'] >= tp_price:
                return True, 'TP'
                
        # SHORT EXIT
        elif self.position == 'SHORT':
            # Stop Loss (Price goes UP)
            sl_price = self.entry_price * (1 + SL_PCT)
            if row['high'] >= sl_price:
                return True, 'SL'

            # Target Profit (Price goes DOWN)
            tp_price = self.entry_price * (1 - TP_PCT)
            if row['low'] <= tp_price:
                return True, 'TP'

        return False, None

    def enter_position(self, price, position_type):
        self.position = position_type
        self.entry_price = price

    def exit_position(self):
        self.position = None
        self.entry_price = 0.0
