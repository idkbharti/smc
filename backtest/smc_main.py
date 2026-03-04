"""
SMC Backtesting Main Runner.

Runs the OB mitigation strategy across multiple assets and timeframes,
printing comprehensive analytics and generating interactive trade charts.

Usage:
    cd /home/dev/Desktop/smc
    python -m backtest.smc_main

    # Specific asset/timeframe + charts:
    python -m backtest.smc_main --asset btc --timeframe 1h --chart

    # Use CSV data:
    python -m backtest.smc_main --source csv --csv-path data/gold_15m.csv --chart
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.data.data_loader import load_data, SYMBOLS, TIMEFRAMES
from backtest.indicators.smc_indicators import compute_all_smc
from backtest.indicators.candle_patterns import detect_candle_patterns
from backtest.strategies.ob_mitigation_strategy import OBMitigationStrategy
from backtest.engine.smc_backtester import SMCBacktester
from backtest.engine.analytics import compute_analytics, print_report, format_report, trades_to_dataframe


def run_single(asset: str, timeframe: str, source: str = 'auto',
               csv_path: str = None, swing_length: int = 50,
               ob_trend_filter: bool = False,
               verbose: bool = False, chart: bool = False):
    """
    Run a single backtest for one asset + timeframe combination.
    """
    label = f"{asset.upper()} {timeframe.upper()}"
    print(f"\n{'─' * 60}")
    print(f"  Loading {label} data...")
    print(f"{'─' * 60}")

    # 1. Load data
    try:
        df = load_data(asset, timeframe, source=source, csv_path=csv_path)
    except Exception as e:
        print(f"  [ERROR] Failed to load data: {e}")
        return None, None, None

    if df.empty or len(df) < swing_length + 10:
        print(f"  [SKIP] Insufficient data ({len(df)} bars, need >{swing_length + 10})")
        return None, None, None

    print(f"  Data range: {df['date'].iloc[0]} → {df['date'].iloc[-1]}")
    print(f"  Total bars: {len(df)}")

    # 2. Compute SMC indicators
    print(f"  Computing SMC indicators (swing length={swing_length}, ob_trend_filter={ob_trend_filter})...")
    df = compute_all_smc(df, swing_length=swing_length, ob_trend_filter=ob_trend_filter)

    # 3. Detect candle patterns
    df = detect_candle_patterns(df)

    # Stats
    bull_obs = df['valid_bull_ob'].sum()
    bear_obs = df['valid_bear_ob'].sum()
    mitigations = df['ob_mitigated_type'].notna().sum()
    hammers = df['bull_hammer'].sum()
    inv_hammers = df['bear_inv_hammer'].sum()
    bull_eng = df['bull_engulfing'].sum()
    bear_eng = df['bear_engulfing'].sum()

    print(f"  Valid OBs detected: {bull_obs} bullish, {bear_obs} bearish")
    print(f"  OB mitigations: {mitigations}")
    print(f"  Hammers: {hammers} | Inv Hammers: {inv_hammers}")
    print(f"  Bull Engulfing: {bull_eng} | Bear Engulfing: {bear_eng}")

    # 4. Run strategy
    strategy = OBMitigationStrategy(mitigation_lookback=5)
    engine = SMCBacktester(df, strategy)
    trades = engine.run()

    print(f"  Trades executed: {len(trades)}")

    # 5. Analytics
    analytics = compute_analytics(trades, label=label)
    print_report(analytics)

    # 6. Trade log
    if trades and verbose:
        trades_df = trades_to_dataframe(trades)
        print(f"\n  Detailed Trade Log ({label}):")
        print(trades_df.to_string(index=False))

    # 7. Charts
    if chart and trades:
        from backtest.engine.visualize import visualize_all_trades
        chart_file = f"smc_trades_{asset}_{timeframe}.html"
        visualize_all_trades(df, trades, label=label, output_path=chart_file)
        print(f"  📊 Charts saved to: {chart_file}")

    return analytics, df, trades


def main():
    parser = argparse.ArgumentParser(description='SMC/ICT Backtesting Engine')
    parser.add_argument('--asset', type=str, default='all',
                        help=f"Asset to test: {list(SYMBOLS.keys())} or 'all' (default: all)")
    parser.add_argument('--timeframe', type=str, default='all',
                        help=f"Timeframe: {list(TIMEFRAMES.keys())} or 'all' (default: all)")
    parser.add_argument('--source', type=str, default='auto',
                        choices=['auto', 'yfinance', 'ccxt', 'csv'],
                        help="Data source (default: auto)")
    parser.add_argument('--csv-path', type=str, default=None,
                        help="Path to CSV file (required if source=csv)")
    parser.add_argument('--swing-length', type=int, default=50,
                        help="Swing structure lookback length (default: 50)")
    parser.add_argument('--ob-trend-filter', action='store_true',
                        help="Only form Bullish OB in uptrend, Bearish OB in downtrend")
    parser.add_argument('--verbose', action='store_true',
                        help="Print detailed trade logs")
    parser.add_argument('--save', action='store_true',
                        help="Save results to backtest_results.txt")
    parser.add_argument('--chart', action='store_true',
                        help="Generate interactive HTML trade charts with OB zones, entries, SL/TP")

    args = parser.parse_args()

    # Determine what to test
    if args.asset == 'all':
        assets = list(SYMBOLS.keys())
    else:
        assets = [args.asset]

    if args.timeframe == 'all':
        timeframes = list(TIMEFRAMES.keys())
    else:
        timeframes = [args.timeframe]

    print("=" * 60)
    print("  SMC/ICT BACKTESTING ENGINE")
    print("  OB Mitigation + Hammer/Engulfing 2-Candle Confirmation")
    print(f"  Assets: {', '.join(a.upper() for a in assets)}")
    print(f"  Timeframes: {', '.join(t.upper() for t in timeframes)}")
    print(f"  Swing Length: {args.swing_length}")
    print(f"  OB Trend Filter: {'ON' if args.ob_trend_filter else 'OFF'}")
    print("=" * 60)

    all_results = []

    for asset in assets:
        for tf in timeframes:
            analytics, df, trades = run_single(
                asset=asset,
                timeframe=tf,
                source=args.source,
                csv_path=args.csv_path,
                swing_length=args.swing_length,
                ob_trend_filter=args.ob_trend_filter,
                verbose=args.verbose,
                chart=args.chart,
            )
            if analytics:
                all_results.append(analytics)

    # ── Summary across all runs ──
    if len(all_results) > 1:
        print(f"\n{'=' * 60}")
        print("  CROSS-TIMEFRAME SUMMARY")
        print(f"{'=' * 60}")
        print(f"  {'Label':<20} {'Trades':>7} {'WR 1:2':>8} {'WR 1:3':>8} {'WR 1:4':>8} {'Expect':>8}")
        print(f"  {'─' * 20} {'─' * 7} {'─' * 8} {'─' * 8} {'─' * 8} {'─' * 8}")
        for r in all_results:
            rr = r.get('rr_stats', {})
            wr12 = rr.get('1:2', {}).get('win_rate', 0)
            wr13 = rr.get('1:3', {}).get('win_rate', 0)
            wr14 = rr.get('1:4', {}).get('win_rate', 0)
            print(f"  {r['label']:<20} {r['total_trades']:>7} {wr12:>7.1f}% {wr13:>7.1f}% {wr14:>7.1f}% {r.get('expectancy_1_2', 0):>7.4f}R")
        print(f"{'=' * 60}")

    # ── Save to file ──
    if args.save and all_results:
        with open('backtest_results.txt', 'w') as f:
            for r in all_results:
                f.write(format_report(r))
                f.write('\n\n')
        print(f"\n  Results saved to backtest_results.txt")


if __name__ == '__main__':
    main()
