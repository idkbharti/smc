"""
Trade Visualization — Interactive candlestick charts with Plotly.

Shows:
  - Candlestick chart with price data
  - OB zones as shaded rectangles
  - Entry/exit markers
  - SL line (red dashed)
  - TP 1:2, 1:3, 1:4 lines (green dashed)
  - Hammer / engulfing markers
  - Trade outcome labels

Generates an interactive HTML file for each trade or all trades together.
"""

import pandas as pd
import numpy as np
from typing import List, Optional
from backtest.strategies.ob_mitigation_strategy import Trade


def _get_plotly():
    """Import plotly with a helpful error message."""
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
        return go, make_subplots
    except ImportError:
        raise ImportError("plotly not installed. Run: pip install plotly")


def visualize_trade(df: pd.DataFrame, trade: Trade,
                    context_bars: int = 30,
                    title: str = '') -> str:
    """
    Create an interactive candlestick chart centered on a single trade.

    Args:
        df: DataFrame with OHLCV + SMC columns
        trade: The trade to visualize
        context_bars: Number of bars before entry and after exit to show
        title: Chart title

    Returns:
        HTML string of the interactive chart
    """
    go, make_subplots = _get_plotly()

    # Determine the window
    start = max(0, trade.hammer_bar - context_bars)
    end = min(len(df) - 1, trade.exit_bar + context_bars) if trade.exit_bar > 0 else min(len(df) - 1, trade.entry_bar + context_bars * 2)
    window = df.iloc[start:end + 1].copy()
    window = window.reset_index(drop=True)

    # Offset indices for the window
    entry_idx = trade.entry_bar - start
    exit_idx = trade.exit_bar - start if trade.exit_bar > 0 else -1
    hammer_idx = trade.hammer_bar - start
    engulfing_idx = trade.engulfing_bar - start

    dates = window['date'] if 'date' in window.columns else window.index

    # ── Candlestick chart ──
    fig = go.Figure()

    # Candlesticks
    fig.add_trace(go.Candlestick(
        x=dates,
        open=window['open'],
        high=window['high'],
        low=window['low'],
        close=window['close'],
        name='Price',
        increasing_line_color='#26a69a',
        decreasing_line_color='#ef5350',
    ))

    # ── OB Zone (shaded rectangle) ──
    ob_color = 'rgba(24, 72, 204, 0.15)' if trade.ob_type == 'BULL' else 'rgba(178, 40, 51, 0.15)'
    ob_border = 'rgba(24, 72, 204, 0.5)' if trade.ob_type == 'BULL' else 'rgba(178, 40, 51, 0.5)'

    fig.add_shape(
        type="rect",
        x0=dates.iloc[max(0, hammer_idx - 10)],
        x1=dates.iloc[min(len(dates) - 1, entry_idx + 5)],
        y0=trade.ob_low,
        y1=trade.ob_high,
        fillcolor=ob_color,
        line=dict(color=ob_border, width=1),
        layer="below",
    )

    # OB label
    fig.add_annotation(
        x=dates.iloc[max(0, hammer_idx - 5)],
        y=trade.ob_high,
        text=f"{'Bull' if trade.ob_type == 'BULL' else 'Bear'} OB",
        showarrow=False,
        font=dict(size=10, color=ob_border.replace('0.5', '1')),
        yshift=10,
    )

    # ── Hammer marker ──
    hammer_color = '#2196F3' if trade.direction == 'LONG' else '#FF5722'
    fig.add_trace(go.Scatter(
        x=[dates.iloc[hammer_idx]],
        y=[window['low'].iloc[hammer_idx] if trade.direction == 'LONG'
           else window['high'].iloc[hammer_idx]],
        mode='markers+text',
        marker=dict(symbol='triangle-up' if trade.direction == 'LONG' else 'triangle-down',
                    size=14, color=hammer_color),
        text=['🔨 Hammer' if trade.direction == 'LONG' else '🔨 Inv Hammer'],
        textposition='bottom center' if trade.direction == 'LONG' else 'top center',
        textfont=dict(size=9),
        name='Reaction Candle',
        showlegend=True,
    ))

    # ── Engulfing marker ──
    fig.add_trace(go.Scatter(
        x=[dates.iloc[engulfing_idx]],
        y=[window['high'].iloc[engulfing_idx] if trade.direction == 'LONG'
           else window['low'].iloc[engulfing_idx]],
        mode='markers+text',
        marker=dict(symbol='star', size=14,
                    color='#4CAF50' if trade.direction == 'LONG' else '#F44336'),
        text=['✅ Bull Engulfing' if trade.direction == 'LONG' else '✅ Bear Engulfing'],
        textposition='top center' if trade.direction == 'LONG' else 'bottom center',
        textfont=dict(size=9),
        name='Confirmation',
        showlegend=True,
    ))

    # ── Entry marker ──
    fig.add_trace(go.Scatter(
        x=[dates.iloc[entry_idx]],
        y=[trade.entry_price],
        mode='markers+text',
        marker=dict(symbol='diamond', size=12,
                    color='#4CAF50' if trade.direction == 'LONG' else '#F44336',
                    line=dict(width=2, color='white')),
        text=[f'ENTRY {trade.direction}\n{trade.entry_price:.2f}'],
        textposition='middle right',
        textfont=dict(size=10, color='#333'),
        name=f'Entry ({trade.direction})',
        showlegend=True,
    ))

    # ── Exit marker ──
    if exit_idx >= 0 and exit_idx < len(dates):
        exit_color = '#F44336' if trade.exit_reason == 'SL' else '#4CAF50'
        exit_symbol = 'x' if trade.exit_reason == 'SL' else 'star'
        fig.add_trace(go.Scatter(
            x=[dates.iloc[exit_idx]],
            y=[trade.exit_price],
            mode='markers+text',
            marker=dict(symbol=exit_symbol, size=14, color=exit_color,
                        line=dict(width=2, color='white')),
            text=[f'EXIT: {trade.exit_reason}\n{trade.exit_price:.2f}'],
            textposition='middle right',
            textfont=dict(size=10, color=exit_color),
            name=f'Exit ({trade.exit_reason})',
            showlegend=True,
        ))

    # ── SL line (red dashed) ──
    line_start = dates.iloc[entry_idx]
    line_end = dates.iloc[min(len(dates) - 1, exit_idx if exit_idx >= 0 else entry_idx + 20)]

    fig.add_shape(
        type="line",
        x0=line_start, x1=line_end,
        y0=trade.sl_price, y1=trade.sl_price,
        line=dict(color='#F44336', width=2, dash='dash'),
    )
    fig.add_annotation(
        x=line_end, y=trade.sl_price,
        text=f"SL: {trade.sl_price:.2f}",
        showarrow=False, font=dict(size=9, color='#F44336'),
        xshift=5, yshift=0,
    )

    # ── TP lines (green dashed) ──
    tp_levels = [
        ('1:2', trade.tp_1_2, trade.hit_1_2),
        ('1:3', trade.tp_1_3, trade.hit_1_3),
        ('1:4', trade.tp_1_4, trade.hit_1_4),
    ]
    tp_colors = ['#66BB6A', '#43A047', '#2E7D32']

    for (label, level, hit), color in zip(tp_levels, tp_colors):
        fig.add_shape(
            type="line",
            x0=line_start, x1=line_end,
            y0=level, y1=level,
            line=dict(color=color, width=1.5, dash='dot'),
        )
        hit_icon = '✓' if hit else '✗'
        fig.add_annotation(
            x=line_end, y=level,
            text=f"TP {label} {hit_icon}: {level:.2f}",
            showarrow=False, font=dict(size=9, color=color),
            xshift=5,
        )

    # ── Entry line ──
    fig.add_shape(
        type="line",
        x0=line_start, x1=line_end,
        y0=trade.entry_price, y1=trade.entry_price,
        line=dict(color='#2196F3', width=1.5, dash='dashdot'),
    )

    # ── Layout ──
    outcome = trade.exit_reason
    rr_text = f"1:2={'✓' if trade.hit_1_2 else '✗'} 1:3={'✓' if trade.hit_1_3 else '✗'} 1:4={'✓' if trade.hit_1_4 else '✗'}"

    if not title:
        title = f"Trade #{trade.entry_bar} — {trade.direction} | {outcome} | {rr_text}"

    fig.update_layout(
        title=dict(text=title, font=dict(size=16)),
        xaxis_title='Date',
        yaxis_title='Price',
        template='plotly_dark',
        xaxis_rangeslider_visible=False,
        height=600,
        width=1200,
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        margin=dict(r=120),  # space for TP labels
    )

    return fig.to_html(full_html=True, include_plotlyjs='cdn')


def visualize_all_trades(df: pd.DataFrame, trades: List[Trade],
                         label: str = '',
                         output_path: str = 'trade_charts.html') -> str:
    """
    Generate a single HTML file with all trade charts stacked vertically.

    Args:
        df: Full DataFrame with OHLCV + indicators
        trades: List of completed trades
        label: Label for the report
        output_path: Where to save the HTML file

    Returns:
        Path to the saved HTML file
    """
    go, _ = _get_plotly()

    if not trades:
        html = "<html><body><h1>No trades to display</h1></body></html>"
        with open(output_path, 'w') as f:
            f.write(html)
        return output_path

    # Build individual charts
    charts_html = []

    # Summary header
    total = len(trades)
    wins_12 = sum(1 for t in trades if t.hit_1_2)
    wins_13 = sum(1 for t in trades if t.hit_1_3)
    wins_14 = sum(1 for t in trades if t.hit_1_4)
    sl_count = sum(1 for t in trades if t.exit_reason == 'SL')

    summary = f"""
    <div style="background:#1a1a2e; padding:20px; border-radius:10px; margin:20px; color:#eee; font-family: 'Inter', sans-serif;">
        <h1 style="color:#00d4ff; margin:0">📊 SMC Trade Analysis — {label}</h1>
        <p style="color:#aaa; margin-top:5px">OB Mitigation + Hammer/Engulfing Confirmation</p>
        <div style="display:flex; gap:30px; margin-top:15px;">
            <div style="background:#16213e; padding:15px 25px; border-radius:8px; text-align:center;">
                <div style="font-size:28px; font-weight:bold; color:#00d4ff">{total}</div>
                <div style="font-size:12px; color:#888">Total Trades</div>
            </div>
            <div style="background:#16213e; padding:15px 25px; border-radius:8px; text-align:center;">
                <div style="font-size:28px; font-weight:bold; color:#4CAF50">{wins_12}</div>
                <div style="font-size:12px; color:#888">Hit 1:2 ({round(wins_12/total*100,1) if total else 0}%)</div>
            </div>
            <div style="background:#16213e; padding:15px 25px; border-radius:8px; text-align:center;">
                <div style="font-size:28px; font-weight:bold; color:#43A047">{wins_13}</div>
                <div style="font-size:12px; color:#888">Hit 1:3 ({round(wins_13/total*100,1) if total else 0}%)</div>
            </div>
            <div style="background:#16213e; padding:15px 25px; border-radius:8px; text-align:center;">
                <div style="font-size:28px; font-weight:bold; color:#2E7D32">{wins_14}</div>
                <div style="font-size:12px; color:#888">Hit 1:4 ({round(wins_14/total*100,1) if total else 0}%)</div>
            </div>
            <div style="background:#16213e; padding:15px 25px; border-radius:8px; text-align:center;">
                <div style="font-size:28px; font-weight:bold; color:#F44336">{sl_count}</div>
                <div style="font-size:12px; color:#888">SL Hit ({round(sl_count/total*100,1) if total else 0}%)</div>
            </div>
        </div>
    </div>
    """
    charts_html.append(summary)

    for idx, trade in enumerate(trades):
        title = f"Trade {idx+1}/{total} — {trade.direction} | {trade.exit_reason} | {trade.entry_date}"
        chart_html = visualize_trade(df, trade, context_bars=30, title=title)

        # Extract just the body content (skip full HTML wrapper)
        # Wrap in a div instead
        trade_info = f"""
        <div style="background:#1a1a2e; padding:15px; margin:10px 20px; border-radius:8px; color:#eee; font-family: 'Inter', sans-serif;">
            <div style="display:flex; gap:20px; align-items:center;">
                <span style="background:{'#4CAF50' if trade.direction=='LONG' else '#F44336'}; padding:4px 12px; border-radius:4px; font-weight:bold; font-size:13px;">
                    {trade.direction}
                </span>
                <span style="color:#aaa; font-size:13px;">
                    Entry: <strong>${trade.entry_price:.2f}</strong> | 
                    SL: <strong style="color:#F44336">${trade.sl_price:.2f}</strong> |
                    TP 1:2: ${trade.tp_1_2:.2f} |
                    TP 1:3: ${trade.tp_1_3:.2f} |
                    TP 1:4: ${trade.tp_1_4:.2f}
                </span>
                <span style="background:{'#4CAF50' if trade.exit_reason != 'SL' else '#F44336'}; padding:4px 12px; border-radius:4px; font-size:13px;">
                    {trade.exit_reason}
                </span>
                <span style="color:#888; font-size:12px;">
                    {'✓ 1:2' if trade.hit_1_2 else '✗ 1:2'} |
                    {'✓ 1:3' if trade.hit_1_3 else '✗ 1:3'} |
                    {'✓ 1:4' if trade.hit_1_4 else '✗ 1:4'}
                </span>
            </div>
        </div>
        """
        charts_html.append(trade_info)
        charts_html.append(chart_html)

    # Combine into single page
    full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>SMC Trade Analysis — {label}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        body {{
            background: #0f0f23;
            margin: 0;
            padding: 0;
            font-family: 'Inter', sans-serif;
        }}
    </style>
</head>
<body>
{''.join(charts_html)}
</body>
</html>"""

    with open(output_path, 'w') as f:
        f.write(full_html)

    print(f"[VIZ] Saved trade charts to {output_path}")
    return output_path
