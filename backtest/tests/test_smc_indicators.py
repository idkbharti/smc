"""
Unit tests for SMC indicators and strategy.
"""

import sys
import os
import numpy as np
import pandas as pd

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.indicators.smc_indicators import (
    detect_swings, detect_trend, detect_zones, detect_valid_obs,
    track_ob_mitigation, compute_all_smc
)
from backtest.indicators.candle_patterns import detect_candle_patterns
from backtest.strategies.ob_mitigation_strategy import OBMitigationStrategy
from backtest.engine.smc_backtester import SMCBacktester
from backtest.engine.analytics import compute_analytics


def make_trending_data(n=300, trend='up'):
    """Create synthetic data with a clear trend that produces swings."""
    np.random.seed(42)
    base = 100.0
    prices = []
    for i in range(n):
        if trend == 'up':
            base += np.random.uniform(-0.3, 0.7)  # net upward
        else:
            base += np.random.uniform(-0.7, 0.3)  # net downward
        # Add some swing noise
        swing = np.sin(i * 0.2) * 3
        price = base + swing
        prices.append(price)

    df = pd.DataFrame({
        'date': pd.date_range('2025-01-01', periods=n, freq='15min'),
        'open': [p + np.random.uniform(-0.5, 0.5) for p in prices],
        'high': [p + np.random.uniform(0.5, 2.0) for p in prices],
        'low': [p - np.random.uniform(0.5, 2.0) for p in prices],
        'close': prices,
        'volume': [1000] * n,
    })
    return df


def test_swing_detection():
    """Test that swing detection finds pivots in trending data."""
    df = make_trending_data(300, 'up')
    df = detect_swings(df, size=10)  # Use smaller size for test data

    assert 'swing_leg' in df.columns
    assert 'is_pivot' in df.columns
    assert 'pivot_type' in df.columns

    pivots = df[df['is_pivot']]
    assert len(pivots) > 0, "Should detect at least some pivots"

    high_pivots = pivots[pivots['pivot_type'] == 'high']
    low_pivots = pivots[pivots['pivot_type'] == 'low']
    assert len(high_pivots) > 0, "Should detect high pivots"
    assert len(low_pivots) > 0, "Should detect low pivots"

    print(f"  ✓ Swing detection: {len(high_pivots)} highs, {len(low_pivots)} lows")


def test_trend_detection():
    """Test that trend detection identifies BOS/CHoCH events."""
    df = make_trending_data(300, 'up')
    df = detect_trend(df, size=10)

    assert 'trend' in df.columns
    assert 'structure' in df.columns

    # In uptrending data, should eventually be BULLISH
    final_trend = df['trend'].iloc[-1]
    assert final_trend != 0, "Trend should not stay neutral with 300 bars"

    structures = df[df['structure'].notna()]
    print(f"  ✓ Trend detection: {len(structures)} BOS/CHoCH events, final trend={final_trend}")


def test_valid_ob_detection():
    """Test that valid OB detection works with compute_all_smc pipeline."""
    df = make_trending_data(300, 'up')
    df = compute_all_smc(df, swing_length=10)

    assert 'valid_bull_ob' in df.columns
    assert 'valid_bear_ob' in df.columns

    bull_obs = df['valid_bull_ob'].sum()
    bear_obs = df['valid_bear_ob'].sum()
    print(f"  ✓ Valid OB detection: {bull_obs} bullish, {bear_obs} bearish")


def test_candle_patterns():
    """Test candle pattern detection with known shapes."""
    # Create a bullish hammer: small body at top, long lower wick
    df = pd.DataFrame({
        'date': pd.date_range('2025-01-01', periods=5, freq='15min'),
        'open':  [100, 100, 99.5, 100, 100],
        'high':  [101, 101, 100,  101, 101],
        'low':   [99,  99,  96,   99,  99],    # bar 2: low wick = 99.5 - 96 = 3.5, body = 0.5
        'close': [100, 100, 100,  100, 100],
        'volume': [1000] * 5,
    })
    df = detect_candle_patterns(df)

    assert df['bull_hammer'].iat[2], "Bar 2 should be a bullish hammer"
    print(f"  ✓ Candle patterns: hammer detected correctly")


def test_full_pipeline():
    """Integration test: run the complete pipeline end to end."""
    df = make_trending_data(500, 'up')
    df = compute_all_smc(df, swing_length=10)
    df = detect_candle_patterns(df)

    strategy = OBMitigationStrategy()
    engine = SMCBacktester(df, strategy)
    trades = engine.run()

    analytics = compute_analytics(trades, label='Test Run')

    print(f"  ✓ Full pipeline: {analytics['total_trades']} trades")
    if analytics['total_trades'] > 0:
        rr = analytics['rr_stats']
        print(f"    Win rates: 1:2={rr['1:2']['win_rate']}%, "
              f"1:3={rr['1:3']['win_rate']}%, "
              f"1:4={rr['1:4']['win_rate']}%")


if __name__ == '__main__':
    print("=" * 50)
    print("  SMC BACKTESTING UNIT TESTS")
    print("=" * 50)

    tests = [
        ('Swing Detection', test_swing_detection),
        ('Trend Detection', test_trend_detection),
        ('Valid OB Detection', test_valid_ob_detection),
        ('Candle Patterns', test_candle_patterns),
        ('Full Pipeline', test_full_pipeline),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        try:
            print(f"\n[TEST] {name}...")
            test_fn()
            passed += 1
        except Exception as e:
            print(f"  ✗ FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'=' * 50}")
    print(f"  Results: {passed} passed, {failed} failed")
    print(f"{'=' * 50}")
