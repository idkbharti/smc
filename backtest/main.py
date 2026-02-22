import pandas as pd
import time
from backtest.config import CLIENT_ID, ACCESS_TOKEN, NIFTY_50_SYMBOLS, TIMEFRAME
from backtest.data.fyers_loader import fetch_historical_data
from backtest.indicators.technicals import calculate_adx, calculate_rsi, calculate_wma, calculate_macd
# from backtest.strategies.adx_rsi_strategy import AdxRsiStrategy
from backtest.strategies.wma_macd_rsi_strategy import WmaMacdRsiStrategy
from backtest.engine.backtester import Backtester

def main():
    try:
        with open("backtest_log.txt", "w") as log_file:
            log_file.write("Starting WMA + MACD + RSI Backtest on Nifty 50 Stocks...\n")
            log_file.write(f"Timeframe: {TIMEFRAME}\n")
            log_file.flush()

            overall_stats = {
                "total_trades": 0,
                "total_pnl_pct": 0.0,
                "wins": 0,
                "losses": 0
            }
            
            results = []

            log_file.write(f"Total Symbols to process: {len(NIFTY_50_SYMBOLS)}\n")
            
            for symbol in NIFTY_50_SYMBOLS:
                log_file.write(f"Processing {symbol}...\n")
                log_file.flush()
                
                # Rate Limiting
                time.sleep(1.0)

                # 1. Fetch Data
                try:
                    df = fetch_historical_data(CLIENT_ID, ACCESS_TOKEN, symbol, timeframe=TIMEFRAME, duration_days=365)
                except Exception as e:
                    log_file.write(f"Error fetching data: {e}\n")
                    log_file.flush()
                    continue
                    
                if df.empty:
                    log_file.write(f"Skipping {symbol} (No Data or Fetch Error)\n")
                    log_file.flush()
                    continue
                
                log_file.write(f"Fetched {len(df)} rows for {symbol}\n")
                    
                # 2. Calculate Indicators
                df = calculate_rsi(df)
                df = calculate_wma(df, period=50)
                df = calculate_wma(df, period=200)
                df = calculate_macd(df)
                
                # 3. Initialize Strategy and Engine
                strategy = WmaMacdRsiStrategy()
                engine = Backtester(df, strategy)
                
                # 4. Run Backtest
                engine.run()
                res = engine.get_results()
                
                # 5. Aggregate Results
                if res['total_trades'] > 0:
                    overall_stats['total_trades'] += res['total_trades']
                    overall_stats['total_pnl_pct'] += res['total_pnl_pct']
                    
                    results.append({
                        "Symbol": symbol,
                        "Trades": res['total_trades'],
                        "Win Rate %": round(res['win_rate'], 2),
                        "PnL %": round(res['total_pnl_pct'], 2)
                    })
                    
            # Print Final Report to Log
            log_file.write("\n" + "="*40 + "\n")
            log_file.write("FINAL BACKTEST REPORT\n")
            log_file.write("="*40 + "\n")
            
            if not results:
                log_file.write("No trades generated or data fetching failed.\n")
            else:
                results_df = pd.DataFrame(results)
                log_file.write(results_df.to_string(index=False))
                
                log_file.write("\n" + "-"*40 + "\n")
                log_file.write(f"Overall Total Trades: {overall_stats['total_trades']}\n")
                log_file.write(f"Overall Total PnL %: {overall_stats['total_pnl_pct']:.2f}\n")
                
                if not results_df.empty:
                    avg_win_rate = results_df['Win Rate %'].mean()
                    log_file.write(f"Average Win Rate: {avg_win_rate:.2f}%\n")
            
            log_file.write("="*40 + "\n")

    except Exception as error:
        print(f"CRITICAL ERROR: {error}")
        with open("backtest_log.txt", "a") as log_file:
            log_file.write(f"\nCRITICAL ERROR: {error}\n")

if __name__ == "__main__":
    main()
