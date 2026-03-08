"""
SMC Custom Terminal  –  TradingView Light Theme Bar Replay
==========================================================
Run:  python3 app.py
Open: http://127.0.0.1:8050
"""
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import MetaTrader5 as mt5

# ─────────────────────────────────────────────────────────────────────────────
# DATA & MT5 INIT
# ─────────────────────────────────────────────────────────────────────────────
if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
    ACCOUNT_INFO = None
    WATCHLIST = ["EURUSD", "GBPUSD"]
else:
    print("MT5 initialized successfully")
    ACCOUNT_INFO = mt5.account_info()
    symbols = mt5.symbols_get()
    if symbols:
        WATCHLIST = [s.name for s in symbols if s.visible]
        if not WATCHLIST: # Fallback if no visible symbols
             WATCHLIST = [s.name for s in symbols[:50]]
    else:
        WATCHLIST = ["EURUSD", "GBPUSD"]

def generate_data(rows: int = 2000) -> pd.DataFrame:
    np.random.seed(99)
    closes = np.cumprod(1 + np.random.normal(0, 0.0018, rows)) * 68000
    start  = datetime(2025, 1, 1)
    out    = []
    for i in range(rows):
        t = start + timedelta(minutes=15 * i)
        c = closes[i]
        o = closes[i-1] if i > 0 else c
        h = max(o, c) + abs(np.random.normal(0, c * 0.0006))
        l = min(o, c) - abs(np.random.normal(0, c * 0.0006))
        out.append({'time': t, 'open': round(o,2), 'high': round(h,2),
                    'low': round(l,2), 'close': round(c,2)})
    return pd.DataFrame(out)

ALL_DATA = generate_data(2000)
BULLISH, BEARISH = 1, -1

def fetch_mt5_data(symbol="EURUSD", timeframe=mt5.TIMEFRAME_M15, bars=200):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
    if rates is None:
        return pd.DataFrame()
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    # Filter columns to only what we need
    return df[['time', 'open', 'high', 'low', 'close']]

# ─────────────────────────────────────────────────────────────────────────────
# SMC ENGINE  –  exact port of stable.pine
# ─────────────────────────────────────────────────────────────────────────────
class OB:
    """Order Block – mirrors stable.pine `orderBlock` type."""
    __slots__ = ('high','low','time','bias','partial','cur_h','cur_l','mitigated')
    def __init__(self, high, low, time, bias):
        self.high=high; self.low=low; self.time=time; self.bias=bias
        self.partial=False; self.mitigated=False
        self.cur_h=high; self.cur_l=low

class StructureEvent:
    __slots__ = ('kind','level','time','direction')
    def __init__(self, kind, level, time, direction):
        self.kind=kind; self.level=level; self.time=time; self.direction=direction

class SMCEngine:
    """
    Mirrors stable.pine logic:
      • leg()            – high[size] > highest(size) → bearish leg start
                           low[size]  < lowest(size)  → bullish leg start
      • Swing pivots     – swingHigh/swingLow current/last levels
      • Trailing extremes– trailing.top = max(high), trailing.bottom = min(low)
                           used for Strong/Weak High/Low lines
      • BOS/CHoCH        – ta.crossover(close, swingHigh) / ta.crossunder
      • OB detection     – bar[-2] sweep + FVG (stable.pine lines 669-680)
      • Mitigation       – High/Low mode (default in stable.pine)
    """
    def __init__(self, length: int = 50, rr: float = 3.0):
        self.length = length
        self.rr     = rr
        self._reset_state()

    def _reset_state(self):
        # Swing pivot state
        self.sh_level    = None   # swingHigh.currentLevel
        self.sh_last     = None   # swingHigh.lastLevel
        self.sh_time     = None
        self.sh_crossed  = False
        self.sl_level    = None   # swingLow.currentLevel
        self.sl_last     = None
        self.sl_time     = None
        self.sl_crossed  = False
        self.trend       = 0      # swingTrend.bias

        # Trailing extremes (for Strong/Weak lines)
        self.trail_top         = None
        self.trail_bottom      = None
        self.trail_top_time    = None
        self.trail_bot_time    = None

        # Output arrays
        self.obs       = []   # active OBs
        self.structure = []   # BOS/CHoCH events
        self.trades    = []

    # ── Pine's leg() function ─────────────────────────────────────────────────
    @staticmethod
    def _leg(H, L, idx, size):
        """
        Mirrors: leg(int size) =>
          if high[size] > ta.highest(size) => 0 (bearish)
          if low[size]  < ta.lowest(size)  => 1 (bullish)
        `highest(size)` in Pine = max of last `size` bars EXCLUDING bar[size]
        i.e. max(H[idx-size+1 .. idx])
        """
        if idx < size: return -1
        pivot_h = H[idx - size]
        pivot_l = L[idx - size]
        # window = bars AFTER pivot but BEFORE current (exclusive of pivot bar)
        win_h = H[idx - size + 1 : idx + 1]
        win_l = L[idx - size + 1 : idx + 1]
        if len(win_h) == 0: return -1
        if pivot_h > win_h.max(): return 0   # bearish leg (high pivot)
        if pivot_l < win_l.min(): return 1   # bullish leg (low pivot)
        return -1

    # ── Main compute ──────────────────────────────────────────────────────────
    def update(self, df: pd.DataFrame, rr: float = None):
        if rr is not None: self.rr = rr
        self._reset_state()

        H = df['high'].values
        L = df['low'].values
        C = df['close'].values
        T = df['time'].values
        n = len(df)
        size = self.length
        prev_leg = -1

        for i in range(n):
            h, l, c, t = H[i], L[i], C[i], T[i]

            # ── Resolve open trades ──────────────────────────────────────────
            for tr in self.trades:
                if tr['result'] == 'open':
                    if tr['dir'] == 'LONG':
                        if h >= tr['tp']:  tr['result'] = 'win'
                        elif l <= tr['sl']: tr['result'] = 'loss'
                    else:
                        if l <= tr['tp']:  tr['result'] = 'win'
                        elif h >= tr['sl']: tr['result'] = 'loss'

            # ── updateTrailingExtremes() ─────────────────────────────────────
            if self.trail_top is None or h > self.trail_top:
                self.trail_top      = h
                self.trail_top_time = t
            if self.trail_bottom is None or l < self.trail_bottom:
                self.trail_bottom   = l
                self.trail_bot_time = t

            # ── getCurrentStructure(size) ────────────────────────────────────
            cur_leg = self._leg(H, L, i, size)
            new_pivot       = (cur_leg != -1 and cur_leg != prev_leg)
            pivot_low       = (cur_leg == 1)
            pivot_high      = (cur_leg == 0)

            if new_pivot:
                pi = i - size
                if self.trend == 0:
                    self.trend = BULLISH if pivot_low else BEARISH

                if pivot_low:
                    self.sl_last   = self.sl_level
                    self.sl_level  = L[pi]
                    self.sl_time   = T[pi]
                    self.sl_crossed = False
                    # sync trailing bottom to pivot low (Pine does this)
                    self.trail_bottom   = L[pi]
                    self.trail_bot_time = T[pi]
                else:
                    self.sh_last   = self.sh_level
                    self.sh_level  = H[pi]
                    self.sh_time   = T[pi]
                    self.sh_crossed = False
                    # sync trailing top to pivot high
                    self.trail_top      = H[pi]
                    self.trail_top_time = T[pi]

            if cur_leg != -1:
                prev_leg = cur_leg

            # ── displayStructure() – BOS / CHoCH ────────────────────────────
            if i > 0:
                pc = C[i-1]
                # Bullish break: close crosses above swingHigh.currentLevel
                if (self.sh_level is not None and not self.sh_crossed
                        and pc <= self.sh_level and c > self.sh_level):
                    kind = 'CHoCH' if self.trend == BEARISH else 'BOS'
                    self.trend      = BULLISH
                    self.sh_crossed = True
                    self.structure.append(
                        StructureEvent(kind, self.sh_level, t, BULLISH))

                # Bearish break: close crosses below swingLow.currentLevel
                if (self.sl_level is not None and not self.sl_crossed
                        and pc >= self.sl_level and c < self.sl_level):
                    kind = 'CHoCH' if self.trend == BULLISH else 'BOS'
                    self.trend      = BEARISH
                    self.sl_crossed = True
                    self.structure.append(
                        StructureEvent(kind, self.sl_level, t, BEARISH))

            # ── OB detection  (stable.pine lines 668-680) ───────────────────
            # bar[2] = i-2, bar[3] = i-3, bar[0] = current (i)
            if i >= 3:
                c2h, c2l = H[i-2], L[i-2]   # OB candle high / low
                c3h, c3l = H[i-3], L[i-3]   # candle before OB

                bull_sweep = c2l < c3l        # OB candle swept prior low
                bull_fvg   = l  > c2h         # FVG: current low above OB high
                bear_sweep = c2h > c3h        # OB candle swept prior high
                bear_fvg   = h  < c2l         # FVG: current high below OB low

                # Track whether OB already stored to avoid duplicates
                ob_time  = T[i-2]

                if bull_sweep and bull_fvg and self.trend == BULLISH:
                    if not any(ob.time == ob_time and ob.bias == BULLISH
                               for ob in self.obs):
                        self.obs.insert(0, OB(c2h, c2l, ob_time, BULLISH))

                if bear_sweep and bear_fvg and self.trend == BEARISH:
                    if not any(ob.time == ob_time and ob.bias == BEARISH
                               for ob in self.obs):
                        self.obs.insert(0, OB(c2h, c2l, ob_time, BEARISH))

            # ── Mitigation (High/Low mode – stable.pine default) ────────────
            # bear mitigation source = high, bull mitigation source = low
            to_rm = []
            for ob in self.obs:
                if ob.bias == BEARISH:
                    if h > ob.high:           # full mitigation
                        ob.mitigated = True; to_rm.append(ob)
                    elif h > ob.low:          # partial – first or continued tap
                        if not ob.partial:
                            ob.cur_h = ob.high
                            ob.cur_l = h
                            self._log(ob, c, BEARISH, t)
                        else:
                            ob.cur_l = max(ob.cur_l, h)
                        ob.partial = True
                else:                         # BULLISH OB
                    if l < ob.low:            # full mitigation
                        ob.mitigated = True; to_rm.append(ob)
                    elif l < ob.high:         # partial tap
                        if not ob.partial:
                            ob.cur_h = l
                            ob.cur_l = ob.low
                            self._log(ob, c, BULLISH, t)
                        else:
                            ob.cur_h = min(ob.cur_h, l)
                        ob.partial = True

            for ob in to_rm:
                if ob in self.obs:
                    self.obs.remove(ob)

    def _log(self, ob, entry, direction, t, live=False, symbol="EURUSD", lot=0.1):
        sl   = ob.high if direction == BEARISH else ob.low
        risk = abs(entry - sl)
        if risk == 0: return
        tp = entry - risk * self.rr if direction == BEARISH else entry + risk * self.rr
        
        trade_dir = 'SHORT' if direction == BEARISH else 'LONG'
        self.trades.append({
            'time':   t,
            'dir':    trade_dir,
            'entry':  entry,
            'sl':     sl,
            'tp':     tp,
            'result': 'open'
        })
        
        # Execute Live Order if requested
        if live:
            order_type = mt5.ORDER_TYPE_SELL if trade_dir == 'SHORT' else mt5.ORDER_TYPE_BUY
            point = mt5.symbol_info(symbol).point
            price = mt5.symbol_info_tick(symbol).bid if trade_dir == 'SHORT' else mt5.symbol_info_tick(symbol).ask

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": float(lot),
                "type": order_type,
                "price": price,
                "sl": float(sl),
                "tp": float(tp),
                "deviation": 20,
                "magic": 234000,
                "comment": f"SMC OB {ob.time}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            result = mt5.order_send(request)
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                print(f"Order failed on {symbol}, lot {lot}: {result.comment}")
            else:
                print(f"Order sent! Ticket: {result.order}")



# ─────────────────────────────────────────────────────────────────────────────
# APP STATE
# ─────────────────────────────────────────────────────────────────────────────
PRIME=200; VISIBLE=120
current_idx=PRIME
engine=SMCEngine(length=15)
visible_df=ALL_DATA.iloc[:PRIME].copy()
engine.update(visible_df)


app=dash.Dash(__name__,title="SMC Terminal")



app.index_string='''
<!DOCTYPE html><html><head>
{%metas%}<title>{%title%}</title>{%favicon%}{%css%}
<style>
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;overflow:hidden;
  background:#f0f3fa;color:#131722;
  font-family:"Trebuchet MS","Helvetica Neue",sans-serif;font-size:13px}
#toolbar{
  display:flex;align-items:center;gap:6px;
  padding:5px 10px;height:44px;
  background:#ffffff;
  border-bottom:1px solid #e0e3eb;flex-wrap:wrap;
}
.logo{font-weight:700;font-size:14px;color:#2962ff;margin-right:8px;letter-spacing:.5px}
.tv-btn{
  padding:4px 12px;font-size:12px;font-weight:600;cursor:pointer;
  border:1px solid #c8cbd6;border-radius:3px;
  background:#ffffff;color:#131722;
  transition:background .15s;
}
.tv-btn:hover{background:#f0f3fa}
.tv-btn.play{background:#2962ff;border-color:#2962ff;color:#fff}
.tv-btn.play:hover{background:#1e53e5}
.tv-btn.reset{background:#ef5350;border-color:#ef5350;color:#fff}
.sep{width:1px;height:22px;background:#e0e3eb;margin:0 4px}
.rr-input{
  width:54px;padding:4px 6px;font-size:12px;font-weight:600;
  border:1px solid #c8cbd6;border-radius:3px;background:#f9fafb;
  color:#131722;text-align:center;
}
.tf-select{
  padding:4px 6px;font-size:12px;font-weight:600;
  border:1px solid #c8cbd6;border-radius:3px;background:#f9fafb;
  color:#131722;cursor:pointer;
}
#stats{margin-left:auto;display:flex;gap:18px;align-items:center;font-size:12px;color:#787b86}
.stat strong{color:#131722}
#stats-bar{
  display:flex;align-items:center;gap:24px;
  padding:5px 14px;
  background:#ffffff;
  border-bottom:1px solid #e0e3eb;
  font-size:12px;color:#787b86;
}
#stats-bar .st{display:flex;gap:5px;align-items:center}
#stats-bar .st strong{font-size:13px;font-weight:700}
.green{color:#26a069!important}.red{color:#ef5350!important}
#chart-wrap{position:absolute;top:88px;left:0;right:0;bottom:0}

/* Profile Hover Styles */
.profile {
  position: relative; display: flex; align-items: center; gap: 8px;
  cursor: pointer; margin-left: auto; color: #131722; font-size: 13px; font-weight: 600;
}
.profile-icon {
  width: 28px; height: 28px; border-radius: 50%; background: #2962ff; color: white;
  display: flex; align-items: center; justify-content: center; font-size: 14px;
}
.badge {
  padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 700; color: white;
}
.badge.demo { background: #ff9800; }
.badge.real { background: #26a069; }
.profile-dropdown {
  display: none; position: absolute; top: 35px; right: 0;
  background: white; border: 1px solid #e0e3eb; border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1); padding: 12px; width: 220px; z-index: 1000;
}
.profile:hover .profile-dropdown { display: block; }
.prof-stat { display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 6px; color: #787b86; }
.prof-stat strong { color: #131722; }
</style>
</head><body>{%app_entry%}
<footer>{%config%}{%scripts%}{%renderer%}</footer>
</body></html>
'''

app.layout=html.Div(style={'height':'100vh'}, children=[
    # ── Toolbar ──────────────────────────────────────────────────────────────
    html.Div(id='toolbar', children=[
        html.Span("⚡ SMC Terminal", className='logo'),
        html.Div(className='sep'),
        # Symbol
        html.Span("Symbol:", style={'fontSize':'12px','color':'#787b86'}),
        dcc.Dropdown(
            id='inp-symbol',
            options=[{'label': s, 'value': s} for s in WATCHLIST],
            value=WATCHLIST[0] if WATCHLIST else "EURUSD",
            clearable=False,
            style={'width':'110px','fontSize':'12px','fontWeight':'600'}
        ),
        html.Div(className='sep'),
        # Timeframe selector
        html.Span("TF:", style={'fontSize':'12px','color':'#787b86'}),
        dcc.Dropdown(
            id='inp-tf',
            options=[
                {'label':'1m',  'value':1},
                {'label':'5m',  'value':5},
                {'label':'15m', 'value':15},
                {'label':'1H',  'value':60},
                {'label':'4H',  'value':240},
            ],
            value=15,
            clearable=False,
            style={'width':'70px','fontSize':'12px','fontWeight':'600'}
        ),
        html.Div(className='sep'),
        # RR input
        html.Span("RR 1:", style={'fontSize':'12px','color':'#787b86'}),
        dcc.Input(id='inp-rr', type='number', value=3, min=0.5, max=20, step=0.5,
                  className='rr-input', debounce=True,
                  placeholder='RR'),
        html.Div(className='sep'),
        # Lot
        html.Span("Lot:", style={'fontSize':'12px','color':'#787b86'}),
        dcc.Input(id='inp-lot', type='number', value=0.1, step=0.01, className='rr-input', debounce=True, style={'width':'50px'}),
        html.Div(className='sep'),
        # Toggles
        dcc.Checklist(
            id='live-toggle',
            options=[
                {'label': ' Live Feed', 'value': 'live'},
                {'label': ' Auto Trade', 'value': 'trade'}
            ],
            value=[],
            inline=True,
            style={'fontSize':'12px','fontWeight':'600', 'color':'#131722', 'display':'flex', 'gap':'8px'}
        ),
        html.Div(className='sep'),
        # Replay Controls
        html.Button("▶  Next Bar",  id='btn-next',   n_clicks=0, className='tv-btn play'),
        html.Button("⏭  +10",       id='btn-n10',    n_clicks=0, className='tv-btn'),
        html.Button("⏭  +50",       id='btn-n50',    n_clicks=0, className='tv-btn'),
        html.Button("⟳  Reset",     id='btn-reset',  n_clicks=0, className='tv-btn reset'),
        html.Div(className='sep'),
        html.Span("Lot:", style={'fontSize':'12px','color':'#787b86', 'marginLeft':'4px'}),
        dcc.Input(id='inp-lot', type='number', value=0.1, step=0.01, className='rr-input', debounce=True, style={'width':'50px'}),
        html.Div(className='sep'),
        dcc.Checklist(
            id='live-toggle',
            options=[
                {'label': ' Live Feed', 'value': 'live'},
                {'label': ' Auto Trade', 'value': 'trade'}
            ],
            value=[],
            inline=True,
            style={'fontSize':'12px','fontWeight':'600', 'color':'#131722', 'display':'flex', 'gap':'8px'}
        ),
        html.Div(className='sep'),
        # Core Stats
        html.Div(id='stats', style={'display': 'flex', 'gap': '18px', 'alignItems': 'center', 'fontSize': '12px', 'color': '#787b86'}, children=[
            html.Div(["Bars: ",    html.Strong("200", id='s-bars')],   className='stat'),
            html.Div(["OBs: ",     html.Strong("0",   id='s-obs')],    className='stat'),
            html.Div(["Trend: ",   html.Strong("—",   id='s-trend', style={'color':'#787b86'})], className='stat'),
            html.Div(["Win %: ",   html.Strong("0%",  id='ss-wr')],      className='stat'),
            html.Div(["PnL (R): ", html.Strong("0R",  id='ss-pnl')],     className='stat'),
        ]),
        html.Div(className='profile', children=[
            html.Div("User", className='profile-icon', id='prof-icon'),
            html.Span("Demo" if getattr(ACCOUNT_INFO, 'trade_mode', 0) == 0 else "Real", 
                      className=f"badge {'demo' if getattr(ACCOUNT_INFO, 'trade_mode', 0) == 0 else 'real'}"),
            html.Div(className='profile-dropdown', children=[
                html.Div(className='prof-stat', children=[html.Span("Name:"), html.Strong(str(getattr(ACCOUNT_INFO, 'name', 'N/A'))[-14:])]),
                html.Div(className='prof-stat', children=[html.Span("Server:"), html.Strong(str(getattr(ACCOUNT_INFO, 'server', 'N/A'))[-14:])]),
                html.Div(style={'height': '1px', 'background': '#e0e3eb', 'margin': '6px 0'}),
                html.Div(className='prof-stat', children=[html.Span("Balance:"), html.Strong(f"{getattr(ACCOUNT_INFO, 'balance', 0.0):.2f}")]),
                html.Div(className='prof-stat', children=[html.Span("Equity:"), html.Strong(f"{getattr(ACCOUNT_INFO, 'equity', 0.0):.2f}")]),
                html.Div(className='prof-stat', children=[html.Span("Currency:"), html.Strong(getattr(ACCOUNT_INFO, 'currency', 'USD'))]),
            ])
        ])
    ]),
    # ── Stats Bar (Hidden) ───────────────────────────────────────────────────
    html.Div(id='stats-bar', style={'display': 'none'}, children=[
        html.Div(["Trades: ",  html.Strong("0", id='ss-trades')],  className='st'),
        html.Div(["Wins: ",    html.Strong("0", id='ss-wins',   style={'color':'#26a069'})], className='st'),
        html.Div(["Losses: ",  html.Strong("0", id='ss-losses', style={'color':'#ef5350'})], className='st'),
        html.Div(["Active: ",  html.Strong("None",id='ss-active')],className='st', style={'marginLeft':'auto','marginRight':'15px'}),
    ]),

    # ── Chart ─────────────────────────────────────────────────────────────────
    html.Div(id='chart-wrap', children=[
        dcc.Graph(id='chart',
                  style={'width':'100%','height':'100%'},
                  config={'scrollZoom':True,
                          'displayModeBar':True,
                          'modeBarButtonsToRemove':['lasso2d','select2d',
                                                    'toggleSpikelines','toImage'],
                          'displaylogo':False})
    ]),

    dcc.Store(id='clk', data={'n':0,'n10':0,'n50':0,'nr':0}),
    dcc.Interval(id='live-interval', interval=1000, n_intervals=0, disabled=True)
])

# ─────────────────────────────────────────────────────────────────────────────
# FIGURE BUILDER  –  TradingView visual style
# ─────────────────────────────────────────────────────────────────────────────
# TradingView OB colors
TV_BEAR_FILL   = 'rgba(239,83,80,0.12)'
TV_BULL_FILL   = 'rgba(41,98,255,0.12)'
TV_BEAR_BORDER = 'rgba(239,83,80,0.7)'
TV_BULL_BORDER = 'rgba(41,98,255,0.7)'
TV_BEAR_MIT    = 'rgba(239,83,80,0.04)'
TV_BULL_MIT    = 'rgba(41,98,255,0.04)'
TV_BOS_BULL    = 'rgba(38,166,154,0.9)'
TV_BOS_BEAR    = 'rgba(239,83,80,0.9)'
TV_CHoCH_BULL  = 'rgba(41,98,255,0.9)'
TV_CHoCH_BEAR  = 'rgba(239,83,80,0.9)'


def build_figure(df: pd.DataFrame, eng: SMCEngine) -> go.Figure:
    fig = go.Figure()
    x_end = df['time'].iloc[-1]
    # small x gap so labels aren't clipped
    dt    = (df['time'].iloc[-1] - df['time'].iloc[-2])

    # ── Candlesticks ──────────────────────────────────────────────────────────
    fig.add_trace(go.Candlestick(
        x=df['time'],
        open=df['open'], high=df['high'],
        low=df['low'],   close=df['close'],
        increasing=dict(line=dict(color='#000000',width=1), fillcolor='#ffffff'),
        decreasing=dict(line=dict(color='#000000',width=1), fillcolor='#000000'),
        showlegend=False, name='',
        hoverlabel=dict(bgcolor='#ffffff', font_color='#131722')
    ))

    shapes=[]; anns=[]

    # ── Active OB rectangles ──────────────────────────────────────────────────
    for ob in eng.obs:
        bull = ob.bias==BULLISH
        # Same color as border, just very low opacity fill
        fill   = 'rgba(41,98,255,0.10)'   if bull else 'rgba(239,83,80,0.10)'
        border = TV_BULL_BORDER if bull else TV_BEAR_BORDER
        # When partially tapped, use an even lighter fill
        if ob.partial:
            fill = 'rgba(41,98,255,0.05)' if bull else 'rgba(239,83,80,0.05)'
        y0 = ob.cur_l if ob.partial else ob.low
        y1 = ob.cur_h if ob.partial else ob.high

        shapes.append(dict(type='rect', xref='x', yref='y',
            x0=ob.time, x1=x_end,
            y0=y0, y1=y1,
            fillcolor=fill,
            line=dict(color=border, width=1),
            layer='below'))

        # Label on right edge (TV style)
        anns.append(dict(
            x=x_end, y=(y0+y1)/2,
            text=f"{'15m' if not ob.partial else '15m·T'}",
            showarrow=False, xanchor='left', yanchor='middle',
            font=dict(size=9, color=border.replace(',0.7)',')')),
            bgcolor='rgba(255,255,255,0.7)', borderpad=2
        ))

    # ── Strong/Weak High/Low lines  (stable.pine: trailing extremes + trend)
    # isStrongHigh = trend BEARISH; isStrongLow = trend BULLISH
    is_bearish = eng.trend == BEARISH
    is_bullish = eng.trend == BULLISH

    if eng.trail_top is not None:
        sh_label = 'Strong High' if is_bearish else 'Weak High'
        sh_clr   = '#ef5350'     if is_bearish else 'rgba(239,83,80,0.5)'
        sh_dash  = 'solid'       if is_bearish else 'dash'
        shapes.append(dict(type='line', xref='x', yref='y',
            x0=eng.trail_top_time, x1=x_end,
            y0=eng.trail_top, y1=eng.trail_top,
            line=dict(color=sh_clr, width=1, dash=sh_dash)))
        anns.append(dict(x=x_end, y=eng.trail_top, text=sh_label,
            showarrow=False, xanchor='left', yanchor='bottom',
            font=dict(size=8, color=sh_clr)))

    if eng.trail_bottom is not None:
        sl_label = 'Strong Low' if is_bullish else 'Weak Low'
        sl_clr   = '#2962ff'    if is_bullish else 'rgba(41,98,255,0.5)'
        sl_dash  = 'solid'      if is_bullish else 'dash'
        shapes.append(dict(type='line', xref='x', yref='y',
            x0=eng.trail_bot_time, x1=x_end,
            y0=eng.trail_bottom, y1=eng.trail_bottom,
            line=dict(color=sl_clr, width=1, dash=sl_dash)))
        anns.append(dict(x=x_end, y=eng.trail_bottom, text=sl_label,
            showarrow=False, xanchor='left', yanchor='top',
            font=dict(size=8, color=sl_clr)))

    # ── BOS / CHoCH ────────────────────────────────────────────────────────────
    for ev in eng.structure[-25:]:
        is_bos  = ev.kind == 'BOS'
        bull    = ev.direction == BULLISH
        clr     = (TV_BOS_BULL if bull else TV_BOS_BEAR) if is_bos \
                  else (TV_CHoCH_BULL if bull else TV_CHoCH_BEAR)
        shapes.append(dict(type='line', xref='x', yref='y',
            x0=ev.time, x1=x_end, y0=ev.level, y1=ev.level,
            line=dict(color=clr, width=1, dash='dot')))
        anns.append(dict(
            x=ev.time, y=ev.level,
            text=ev.kind,
            showarrow=False, xanchor='left', yanchor='bottom',
            font=dict(size=9, color=clr, family='monospace'),
            bgcolor='rgba(255,255,255,0.85)', borderpad=2,
            bordercolor=clr, borderwidth=0
        ))

    # ── Trade Markers ─────────────────────────────────────────────────────────
    for tr in eng.trades[-60:]:
        long = tr['dir']=='LONG'
        clr  = '#2962ff' if long else '#ef5350'
        fig.add_trace(go.Scatter(
            x=[tr['time']], y=[tr['entry']], mode='markers',
            marker=dict(symbol='triangle-up' if long else 'triangle-down',
                        size=11, color=clr, line=dict(color=clr, width=1)),
            showlegend=False,
            hovertemplate=(f"{tr['dir']}<br>Entry: {{y:.2f}}"
                           f"<br>SL: {tr['sl']:.2f}<br>TP: {tr['tp']:.2f}<extra></extra>")
        ))

    # ── Layout ────────────────────────────────────────────────────────────────
    x_start = df['time'].iloc[max(0, len(df)-VISIBLE)]

    fig.update_layout(
        shapes=shapes, annotations=anns,
        template=None,
        plot_bgcolor  = '#ffffff',   # TV white chart area
        paper_bgcolor = '#f0f3fa',   # TV slightly grey outer area
        font=dict(color='#131722', size=11, family='Trebuchet MS'),
        margin=dict(l=0, r=65, t=0, b=0),
        xaxis=dict(
            range=[x_start, x_end + dt*6],
            rangeslider_visible=False,
            showgrid=True, gridcolor='#f0f3fa', gridwidth=1,
            zeroline=False, showline=True, linecolor='#e0e3eb',
            tickfont=dict(color='#787b86', size=10),
            type='date',
        ),
        yaxis=dict(
            side='right', autorange=True,
            showgrid=True, gridcolor='#f0f3fa', gridwidth=1,
            zeroline=False, showline=True, linecolor='#e0e3eb',
            tickfont=dict(color='#787b86', size=10),
        ),
        hoverlabel=dict(bgcolor='#ffffff', bordercolor='#e0e3eb',
                        font=dict(color='#131722', size=11)),
        hovermode='x',
        dragmode='pan',
    )
    return fig

def _calc_stats(trades, rr, current_close):
    """Determine wins/losses by checking if price hit TP or SL first.
    Since we only have the entry/sl/tp stored per trade and no future bar data
    here without full scan, we approximate using subsequent candles.
    For now we mark a trade as WIN if tp was closer to entry than sl.
    Full bar-by-bar resolution is handled in the engine itself in a future pass."""
    wins=0; losses=0; pnl=0.0
    act_str = "None"; act_clr = "#787b86"
    
    for t in trades:
        risk = abs(t['entry'] - t['sl'])
        if risk == 0: continue
        # Resolved: engine marks result if 'result' key set, else 'open'
        result = t.get('result','open')
        if result == 'win':   wins+=1;   pnl += rr
        elif result == 'loss': losses+=1; pnl -= 1
        elif result == 'open':
            if t['dir'] == 'LONG':
                floating_r = (current_close - t['entry']) / risk
            else:
                floating_r = (t['entry'] - current_close) / risk
                
            act_str = f"{t['dir']}  {floating_r:+.1f}R"
            act_clr = '#26a069' if floating_r >= 0 else '#ef5350'
            
    total = wins+losses
    wr = f"{round(wins/total*100) if total else 0}%"
    pnl_str = f"{pnl:+.1f}R"
    pnl_color = '#26a069' if pnl>=0 else '#ef5350'
    return total, wins, losses, wr, pnl_str, pnl_color, act_str, act_clr


# ─────────────────────────────────────────────────────────────────────────────
# CALLBACK
# ─────────────────────────────────────────────────────────────────────────────
@app.callback(
    [Output('chart','figure'),
     Output('s-bars','children'), Output('s-obs','children'),
     Output('s-trend','children'), Output('s-trend','style'),
     Output('ss-trades','children'), Output('ss-wins','children'),
     Output('ss-losses','children'), Output('ss-wr','children'),
     Output('ss-pnl','children'), Output('ss-pnl','style'),
     Output('ss-active','children'), Output('ss-active','style'),
     Output('clk','data'), Output('live-interval', 'disabled')],
    [Input('btn-next','n_clicks'), Input('btn-n10','n_clicks'),
     Input('btn-n50','n_clicks'),  Input('btn-reset','n_clicks'),
     Input('live-interval', 'n_intervals'),
     Input('inp-symbol', 'value'), Input('inp-tf', 'value')],
    [State('clk','data'), State('inp-rr','value'),
     State('live-toggle', 'value'), State('inp-lot', 'value')]
)
def on_click(n, n10, n50, nr, n_int, symbol, tf_val, prev, rr_val, live_toggles, lot_val):
    global current_idx, visible_df, engine
    rr = float(rr_val) if rr_val else 3.0
    lot = float(lot_val) if lot_val else 0.1
    pn,pn10,pn50,pr = prev.get('n',0),prev.get('n10',0),prev.get('n50',0),prev.get('nr',0)
    
    is_live_feed = 'live' in live_toggles
    is_auto_trade = 'trade' in live_toggles
    
    tf_map = {1: mt5.TIMEFRAME_M1, 5: mt5.TIMEFRAME_M5, 15: mt5.TIMEFRAME_M15, 60: mt5.TIMEFRAME_H1, 240: mt5.TIMEFRAME_H4}
    mt5_tf = tf_map.get(int(tf_val), mt5.TIMEFRAME_M15)
    
    ctx = dash.callback_context
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None

    # Reset Action (User changed config or clicked Reset)
    config_changed = (triggered_id in ['btn-reset', 'live-toggle', 'inp-symbol', 'inp-tf'])
    if nr > pr or config_changed:
        df = fetch_mt5_data(symbol, mt5_tf, 2000)
        global ALL_DATA
        if not df.empty:
            ALL_DATA = df
        else:
            ALL_DATA = generate_data(2000)
            
        current_idx = PRIME
        visible_df = ALL_DATA.iloc[:PRIME].copy()
            
        engine=SMCEngine(length=50, rr=rr)
        # We don't want to execute live orders on past loaded data
        engine.update(visible_df, rr=rr)
        
        # Monkey patch _log to execute on live ticks going forward
        def _live_log(ob, entry, direction, t):
            # Hack to allow modifying method dynamically while preserving context
            SMCEngine._log(engine, ob, entry, direction, t, live=is_auto_trade, symbol=symbol, lot=lot)
        engine._log = _live_log
        
    else:
        # Standard Next Bar / Live Interval Action
        if is_live_feed and triggered_id == 'live-interval':
            new_df = fetch_mt5_data(symbol, mt5_tf, PRIME)
            if not new_df.empty:
                visible_df = new_df
                engine.update(visible_df, rr=rr)
        elif not is_live_feed:
            advance=0
            if n>pn:     advance=1
            if n10>pn10: advance=10
            if n50>pn50: advance=50
            if advance:
                end=min(current_idx+advance,len(ALL_DATA))
                new_bars = ALL_DATA.iloc[current_idx:end]
                visible_df=pd.concat([visible_df,new_bars],ignore_index=True)
                current_idx=end
                engine.update(visible_df, rr=rr)   # resolves SL/TP internally

    total,wins,losses,wr,pnl_str,pnl_clr,act_str,act_clr = _calc_stats(engine.trades, rr, visible_df['close'].iloc[-1])

    trend_txt = '▲ BULLISH' if engine.trend==BULLISH \
           else '▼ BEARISH' if engine.trend==BEARISH else '—'
    trend_clr = '#26a069' if engine.trend==BULLISH \
           else '#ef5350' if engine.trend==BEARISH else '#787b86'

    return (
        build_figure(visible_df, engine),
        str(len(visible_df)), str(len(engine.obs)),
        trend_txt, {'color':trend_clr,'fontWeight':'600'},
        str(total), str(wins), str(losses), wr,
        pnl_str, {'color':pnl_clr,'fontWeight':'700'},
        act_str, {'color':act_clr,'fontWeight':'700'},
        {'n':n,'n10':n10,'n50':n50,'nr':nr},
        not is_live_feed  # Disabled if not live
    )

if __name__=='__main__':
    print('\n⚡ SMC Terminal  →  http://127.0.0.1:8050/\n')
    app.run(debug=False, port=8050)
