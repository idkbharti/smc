import pandas as pd
from backtest.strategies.adx_rsi_strategy import AdxRsiStrategy
from backtest.config import SL_PCT, TP_PCT

class Backtester:
    def __init__(self, data, strategy):
        self.data = data
        self.strategy = strategy
        self.trades = []
        self.balance = 100000  # Initial capital for simulation
        self.equity_curve = []

    def run(self):
        """
        Iterates through the dataframe and executes the strategy.
        """
        for i in range(1, len(self.data)):
            prev_row = self.data.iloc[i-1]
            row = self.data.iloc[i]
            
            # Check Exit
            if self.strategy.position is not None:
                exit_signal, reason = self.strategy.check_exit(row)
                if exit_signal:
                    exit_price = 0
                    if self.strategy.position == 'LONG':
                        if reason == 'SL':
                            exit_price = self.strategy.entry_price * (1 - SL_PCT)
                        elif reason == 'TP':
                            exit_price = self.strategy.entry_price * (1 + TP_PCT)
                    elif self.strategy.position == 'SHORT':
                        if reason == 'SL':
                            exit_price = self.strategy.entry_price * (1 + SL_PCT)
                        elif reason == 'TP':
                            exit_price = self.strategy.entry_price * (1 - TP_PCT)
                    
                    self._record_trade(row['date'], 'EXIT', exit_price, reason, self.strategy.position)
                    self.strategy.exit_position()

            # Check Entry
            elif self.strategy.position is None:
                entry_signal, direction = self.strategy.check_entry(row, prev_row)
                if entry_signal:
                    self.strategy.enter_position(row['close'], direction)
                    self._record_trade(row['date'], 'ENTRY', row['close'], 'ENTRY', direction)

    def _record_trade(self, date, type, price, reason, direction):
        trade = {
            'date': date,
            'type': type,
            'price': price,
            'reason': reason,
            'direction': direction
        }
        self.trades.append(trade)

    def get_results(self):
        """
        Calculates performance metrics.
        """
        df_trades = pd.DataFrame(self.trades)
        if df_trades.empty:
            return {"total_trades": 0, "total_pnl_pct": 0, "win_rate": 0}

        # Calculate PnL per trade pair
        pnl_list = []
        entry_price = 0
        
        # Iterate through trades to match Entry/Exit
        for i in range(0, len(df_trades) - 1, 2):
            entry_trade = df_trades.iloc[i]
            exit_trade = df_trades.iloc[i+1]
            
            if entry_trade['type'] != 'ENTRY' or exit_trade['type'] != 'EXIT':
                continue
                
            entry_price = entry_trade['price']
            exit_price = exit_trade['price']
            direction = entry_trade['direction']
            
            pnl = 0.0
            if direction == 'LONG':
                pnl = (exit_price - entry_price) / entry_price * 100
            elif direction == 'SHORT':
                pnl = (entry_price - exit_price) / entry_price * 100
                
            pnl_list.append(pnl)

        total_trades = len(pnl_list)
        wins = len([p for p in pnl_list if p > 0])
        total_pnl = sum(pnl_list)
        
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        
        return {
            "total_trades": total_trades,
            "total_pnl_pct": total_pnl,
            "win_rate": win_rate,
            "trades": df_trades
        }
