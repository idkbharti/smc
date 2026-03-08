import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import TopBar from './components/TopBar';
import Toolbar from './components/Toolbar';
import StatsBar from './components/StatsBar';
import Chart from './components/Chart';
import type { CandlestickData, Time } from 'lightweight-charts';

const API_BASE = 'http://127.0.0.1:8085/api';

function App() {
  // Config State
  const [symbol, setSymbol] = useState('EURUSD');
  const [tf, setTf] = useState(15);
  const [rr, setRr] = useState(3.0);
  const [lot, setLot] = useState(0.1);
  const [smcLength, setSmcLength] = useState(20);
  const [showFull, setShowFull] = useState(true);
  const [showPartial, setShowPartial] = useState(true);
  const [watchlist, setWatchlist] = useState<string[]>([]);
  const [liveFeed, setLiveFeed] = useState(false);
  const [autoTrade, setAutoTrade] = useState(false);
  const [speed, setSpeed] = useState(1000);

  // Data State
  const [candlesticks, setCandlesticks] = useState<CandlestickData<Time>[]>([]);
  const [currentIndex, setCurrentIndex] = useState(1000);
  const [analysis, setAnalysis] = useState<any>({ 
    obs: [], 
    structure: [], 
    trend: 'neutral', 
    stats: {}, 
    trails: { top: null, top_time: null, bottom: null, bottom_time: null },
    receivedSymbol: '' 
  });

  // Init
  useEffect(() => {
    axios.get(`${API_BASE}/init`).then(res => {
      setWatchlist(res.data.watchlist);
      if (res.data.watchlist.length > 0) setSymbol(res.data.watchlist[0]);
    });
  }, []);

  const resetData = useCallback(async () => {
    try {
        const res = await axios.get(`${API_BASE}/history?symbol=${symbol}&timeframe=${tf}`);
        setCandlesticks(res.data.candles);
        setCurrentIndex(1000);
    } catch (err) {
        console.error("Reset failed", err);
    }
  }, [symbol, tf]);

  useEffect(() => {
    resetData();
  }, [resetData]);

  // SMC Update
  useEffect(() => {
    if (candlesticks.length > 0) {
        axios.post(`${API_BASE}/engine/analyze`, {
            symbol, timeframe: tf, currentIndex, rr, length: smcLength
        }).then(res => {
            setAnalysis({ ...res.data, receivedSymbol: symbol });
        });
    }
  }, [currentIndex, candlesticks, symbol, tf, rr, smcLength]);

  const effectiveAnalysis = analysis.receivedSymbol === symbol ? analysis : {
    obs: [],
    structure: [],
    trend: 'neutral',
    trails: { top: null, top_time: null, bottom: null, bottom_time: null },
    receivedSymbol: ''
  };

  const handleNext = (count: number) => {
    setCurrentIndex(prev => Math.min(prev + count, candlesticks.length));
  };

  // Live interval (Bar Replay)
  useEffect(() => {
    if (liveFeed) {
        const interval = setInterval(() => {
            setCurrentIndex(prev => Math.min(prev + 1, candlesticks.length));
        }, speed);
        return () => clearInterval(interval);
    }
  }, [liveFeed, speed, candlesticks.length]);

  return (
    <div className="flex flex-col h-screen bg-tv-panel">
      <TopBar 
        symbol={symbol} setSymbol={setSymbol} 
        timeframe={tf} setTimeframe={setTf} 
        watchlist={watchlist} 
      />
      
        <Toolbar 
          onNext={handleNext} onReset={resetData} 
          rr={rr} setRr={setRr} 
          lot={lot} setLot={setLot} 
          smcLength={smcLength} setSmcLength={setSmcLength}
          showFull={showFull} setShowFull={setShowFull}
          showPartial={showPartial} setShowPartial={setShowPartial}
          liveFeed={liveFeed} setLiveFeed={setLiveFeed} 
          autoTrade={autoTrade} setAutoTrade={setAutoTrade} 
          speed={speed} setSpeed={setSpeed}
        />

      <StatsBar 
        trades={analysis.trades?.length || 0}
        wins={analysis.trades?.filter((t: any) => t.result === 'win').length || 0} 
        losses={analysis.trades?.filter((t: any) => t.result === 'loss').length || 0}
        winRate={
          analysis.trades?.length > 0 
            ? `${((analysis.trades.filter((t: any) => t.result === 'win').length / analysis.trades.length) * 100).toFixed(1)}%` 
            : '0%'
        }
        pnl={
          (analysis.trades?.reduce((acc: number, t: any) => {
            if (t.result === 'win') return acc + rr;
            if (t.result === 'loss') return acc - 1;
            return acc;
          }, 0) || 0).toFixed(1) + 'R'
        }
      />

      <div className="flex-1 flex overflow-hidden relative">
        <Chart 
            data={candlesticks.slice(0, currentIndex)} 
            obs={effectiveAnalysis.obs} 
            structure={effectiveAnalysis.structure} 
            trend={effectiveAnalysis.trend}
            trails={effectiveAnalysis.trails}
            settings={{ showFull, showPartial }}
        />

        {/* MTF Trend Indicators */}
        <div className="absolute top-3 right-3 z-10 flex gap-2">
            <div className={`px-2 py-1 rounded text-[10px] font-bold border ${effectiveAnalysis.trend === 'bullish' ? 'bg-tv-green/10 border-tv-green text-tv-green' : effectiveAnalysis.trend === 'bearish' ? 'bg-tv-red/10 border-tv-red text-tv-red' : 'bg-gray-100 border-gray-300 text-gray-500'}`}>
                15m
            </div>
            <div className="px-2 py-1 rounded text-[10px] font-bold border bg-gray-100 border-gray-300 text-gray-500">
                1h
            </div>
            <div className="px-2 py-1 rounded text-[10px] font-bold border bg-gray-100 border-gray-300 text-gray-500">
                1d
            </div>
        </div>
      </div>
    </div>
  );
}

export default App;
