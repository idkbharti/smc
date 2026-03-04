"""
SMC Backtester Engine — Runs OB mitigation strategy over prepared data.

Unlike the generic backtester.py, this engine:
  - Uses R:R based SL/TP (not percentage)
  - Tracks 1:2, 1:3, 1:4 targets independently per trade
  - Records detailed trade logs for analytics
"""

import pandas as pd
from backtest.strategies.ob_mitigation_strategy import OBMitigationStrategy, Trade
from typing import List


class SMCBacktester:
    """
    Iterates bar-by-bar over a DataFrame that already has all SMC indicator
    and candle-pattern columns computed, executing the OB mitigation strategy.
    """

    def __init__(self, data: pd.DataFrame, strategy: OBMitigationStrategy):
        self.data = data
        self.strategy = strategy

    def run(self) -> List[Trade]:
        """
        Execute the strategy across all bars.
        Returns the list of completed trades.
        """
        df = self.data
        n = len(df)

        for i in range(1, n):
            # ── Check exit first ──
            if self.strategy.position is not None:
                closed = self.strategy.check_exit(i, df)
                if closed:
                    continue  # Don't enter on the same bar we exit

            # ── Check entry ──
            if self.strategy.position is None:
                trade = self.strategy.check_entry(i, df)
                if trade is not None:
                    self.strategy.enter(trade)

        # Force close any remaining position at end of data
        if self.strategy.position is not None:
            self.strategy.force_close(n - 1, df)

        return self.strategy.completed_trades
