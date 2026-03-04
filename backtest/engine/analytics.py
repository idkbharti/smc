"""
Analytics Module — generates comprehensive statistics from trade results.
"""

import pandas as pd
from typing import List, Dict, Any
from backtest.strategies.ob_mitigation_strategy import Trade


def compute_analytics(trades: List[Trade], label: str = '') -> Dict[str, Any]:
    """
    Compute performance statistics from a list of completed trades.

    Returns a dictionary with per-R:R stats, direction breakdown, etc.
    """
    if not trades:
        return {
            'label': label,
            'total_trades': 0,
            'rr_stats': {},
            'direction_stats': {},
            'confirmation_stats': {},
        }

    total = len(trades)

    # ── Per R:R Ratio Stats ──
    rr_stats = {}
    for rr_name, attr in [('1:2', 'hit_1_2'), ('1:3', 'hit_1_3'), ('1:4', 'hit_1_4')]:
        hits = sum(1 for t in trades if getattr(t, attr))
        sl_count = sum(1 for t in trades if t.exit_reason == 'SL')
        wins = hits
        # Trades that didn't hit this target AND didn't hit SL are still open/ended
        rr_stats[rr_name] = {
            'wins': wins,
            'losses': sl_count,
            'total': total,
            'win_rate': round(wins / total * 100, 2) if total > 0 else 0,
            'sl_rate': round(sl_count / total * 100, 2) if total > 0 else 0,
        }

    # ── Direction Breakdown ──
    long_trades = [t for t in trades if t.direction == 'LONG']
    short_trades = [t for t in trades if t.direction == 'SHORT']

    direction_stats = {
        'long': {
            'total': len(long_trades),
            'sl': sum(1 for t in long_trades if t.exit_reason == 'SL'),
            'hit_1_2': sum(1 for t in long_trades if t.hit_1_2),
            'hit_1_3': sum(1 for t in long_trades if t.hit_1_3),
            'hit_1_4': sum(1 for t in long_trades if t.hit_1_4),
        },
        'short': {
            'total': len(short_trades),
            'sl': sum(1 for t in short_trades if t.exit_reason == 'SL'),
            'hit_1_2': sum(1 for t in short_trades if t.hit_1_2),
            'hit_1_3': sum(1 for t in short_trades if t.hit_1_3),
            'hit_1_4': sum(1 for t in short_trades if t.hit_1_4),
        },
    }

    # ── Confirmation Pattern Stats ──
    confirm_types = set(t.confirmation for t in trades)
    confirmation_stats = {}
    for ctype in confirm_types:
        ct_trades = [t for t in trades if t.confirmation == ctype]
        confirmation_stats[ctype] = {
            'total': len(ct_trades),
            'hit_1_2': sum(1 for t in ct_trades if t.hit_1_2),
            'hit_1_3': sum(1 for t in ct_trades if t.hit_1_3),
            'hit_1_4': sum(1 for t in ct_trades if t.hit_1_4),
            'sl': sum(1 for t in ct_trades if t.exit_reason == 'SL'),
        }

    # ── Max Consecutive ──
    wins_streak = 0
    loss_streak = 0
    max_win_streak = 0
    max_loss_streak = 0
    for t in trades:
        if t.hit_1_2:
            wins_streak += 1
            loss_streak = 0
        elif t.exit_reason == 'SL':
            loss_streak += 1
            wins_streak = 0
        max_win_streak = max(max_win_streak, wins_streak)
        max_loss_streak = max(max_loss_streak, loss_streak)

    # ── Expectancy (based on 1:2 as the main target) ──
    rr_1_2 = rr_stats.get('1:2', {})
    win_rate_1_2 = rr_1_2.get('win_rate', 0) / 100
    # Expectancy = (Win% × R) - (Loss% × 1)
    expectancy_1_2 = (win_rate_1_2 * 2) - ((1 - win_rate_1_2) * 1)

    return {
        'label': label,
        'total_trades': total,
        'rr_stats': rr_stats,
        'direction_stats': direction_stats,
        'confirmation_stats': confirmation_stats,
        'max_win_streak': max_win_streak,
        'max_loss_streak': max_loss_streak,
        'expectancy_1_2': round(expectancy_1_2, 4),
    }


def format_report(analytics: Dict[str, Any]) -> str:
    """Format analytics into a readable text report."""
    lines = []
    label = analytics.get('label', '')
    lines.append(f"{'=' * 60}")
    lines.append(f"  SMC OB MITIGATION STRATEGY — {label}")
    lines.append(f"{'=' * 60}")
    lines.append(f"  Total Trades: {analytics['total_trades']}")
    lines.append("")

    if analytics['total_trades'] == 0:
        lines.append("  No trades generated.")
        lines.append(f"{'=' * 60}")
        return '\n'.join(lines)

    # R:R Stats
    lines.append("  ┌─────────┬───────┬────────┬────────┬──────────┐")
    lines.append("  │  Target │ Wins  │ Losses │ Total  │ Win Rate │")
    lines.append("  ├─────────┼───────┼────────┼────────┼──────────┤")
    for rr_name, stats in analytics['rr_stats'].items():
        lines.append(
            f"  │   {rr_name:>4}  │ {stats['wins']:>5} │ {stats['losses']:>6} │ {stats['total']:>6} │ {stats['win_rate']:>7.1f}% │"
        )
    lines.append("  └─────────┴───────┴────────┴────────┴──────────┘")
    lines.append("")

    # Direction
    lines.append("  Direction Breakdown:")
    for d, stats in analytics['direction_stats'].items():
        if stats['total'] > 0:
            wr = round(stats['hit_1_2'] / stats['total'] * 100, 1)
            lines.append(
                f"    {d.upper():>5}: {stats['total']} trades | "
                f"1:2 {stats['hit_1_2']}W | 1:3 {stats['hit_1_3']}W | "
                f"1:4 {stats['hit_1_4']}W | SL {stats['sl']} | WR(1:2) {wr}%"
            )
    lines.append("")

    # Confirmation patterns
    lines.append("  Confirmation Pattern Breakdown:")
    for ctype, stats in analytics['confirmation_stats'].items():
        if stats['total'] > 0:
            wr = round(stats['hit_1_2'] / stats['total'] * 100, 1)
            lines.append(
                f"    {ctype:>12}: {stats['total']} trades | "
                f"1:2 {stats['hit_1_2']}W | 1:3 {stats['hit_1_3']}W | "
                f"1:4 {stats['hit_1_4']}W | SL {stats['sl']} | WR(1:2) {wr}%"
            )
    lines.append("")

    # Streaks & Expectancy
    lines.append(f"  Max Win Streak:  {analytics['max_win_streak']}")
    lines.append(f"  Max Loss Streak: {analytics['max_loss_streak']}")
    lines.append(f"  Expectancy (1:2): {analytics['expectancy_1_2']:.4f} R")
    lines.append(f"{'=' * 60}")

    return '\n'.join(lines)


def print_report(analytics: Dict[str, Any]):
    """Print formatted report to console."""
    print(format_report(analytics))


def trades_to_dataframe(trades: List[Trade]) -> pd.DataFrame:
    """Convert trade list to a DataFrame for inspection/export."""
    if not trades:
        return pd.DataFrame()

    records = []
    for t in trades:
        records.append({
            'entry_bar': t.entry_bar,
            'entry_date': t.entry_date,
            'entry_price': round(t.entry_price, 4),
            'direction': t.direction,
            'sl_price': round(t.sl_price, 4),
            'sl_distance': round(t.sl_distance, 4),
            'tp_1_2': round(t.tp_1_2, 4),
            'tp_1_3': round(t.tp_1_3, 4),
            'tp_1_4': round(t.tp_1_4, 4),
            'ob_type': t.ob_type,
            'confirmation': t.confirmation,
            'exit_bar': t.exit_bar,
            'exit_date': t.exit_date,
            'exit_price': round(t.exit_price, 4),
            'exit_reason': t.exit_reason,
            'hit_1_2': t.hit_1_2,
            'hit_1_3': t.hit_1_3,
            'hit_1_4': t.hit_1_4,
            'max_favorable': round(t.max_favorable, 4),
            'max_adverse': round(t.max_adverse, 4),
        })

    return pd.DataFrame(records)
