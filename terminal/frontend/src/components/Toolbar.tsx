import React from 'react';
import { Play, FastForward, RotateCcw } from 'lucide-react';

interface ToolbarProps {
  onNext: (count: number) => void;
  onReset: () => void;
  rr: number;
  setRr: (rr: number) => void;
  lot: number;
  setLot: (l: number) => void;
  liveFeed: boolean;
  setLiveFeed: (b: boolean) => void;
  autoTrade: boolean;
  setAutoTrade: (b: boolean) => void;
  speed: number;
  setSpeed: (s: number) => void;
  smcLength: number;
  setSmcLength: (l: number) => void;
  showFull: boolean;
  setShowFull: (b: boolean) => void;
  showPartial: boolean;
  setShowPartial: (b: boolean) => void;
}

const Toolbar: React.FC<ToolbarProps> = ({ 
  onNext, onReset, rr, setRr, lot, setLot, 
  liveFeed, setLiveFeed, autoTrade, setAutoTrade,
  speed, setSpeed, smcLength, setSmcLength,
  showFull, setShowFull, showPartial, setShowPartial
}) => {
  return (
    <div className="h-9 border-b border-tv-border bg-[#ffffff] flex items-center px-3 gap-2">
      {/* Replay Buttons */}
      <button onClick={() => onNext(1)} className="tv-btn tv-btn-blue flex items-center gap-1">
        <Play size={10} fill="currentColor" /> Next Bar
      </button>
      <button onClick={() => onNext(10)} className="tv-btn flex items-center gap-1">
        <FastForward size={12} /> +10
      </button>
      <button onClick={() => onNext(50)} className="tv-btn flex items-center gap-1">
        <FastForward size={12} /> +50
      </button>
      <button onClick={onReset} className="tv-btn tv-btn-red flex items-center gap-1">
        <RotateCcw size={12} /> Reset
      </button>

      <div className="sep" />

      {/* Speed Select */}
      <span className="text-[11px] text-tv-muted font-semibold uppercase">Speed</span>
      <select 
        className="tv-select w-20"
        value={speed}
        onChange={(e) => setSpeed(Number(e.target.value))}
      >
        <option value={2000}>Slower</option>
        <option value={1000}>Normal</option>
        <option value={500}>Fast</option>
        <option value={200}>Turbo</option>
        <option value={50}>Instant</option>
      </select>

      <div className="sep" />

      {/* RR 1:N */}
      <span className="text-[11px] text-tv-muted font-semibold uppercase">RR 1:</span>
      <input 
        type="number" 
        className="tv-select w-12 text-center" 
        value={rr} 
        onChange={(e) => setRr(Number(e.target.value))}
        step={0.5}
      />

      <div className="sep" />

      {/* Lot Size */}
      <span className="text-[11px] text-tv-muted font-semibold uppercase">Lot:</span>
      <input 
        type="number" 
        className="tv-select w-14 text-center" 
        value={lot} 
        onChange={(e) => setLot(Number(e.target.value))}
        step={0.01}
      />

      <div className="sep" />

      {/* Toggles */}
      <div className="flex items-center gap-4 ml-2">
        <label className="flex items-center gap-1.5 cursor-pointer">
          <input 
            type="checkbox" 
            checked={liveFeed} 
            onChange={(e) => setLiveFeed(e.target.checked)}
            className="w-3.5 h-3.5 accent-tv-blue border-tv-border cursor-pointer"
          />
          <span className="text-[11px] font-bold text-tv-text uppercase tracking-tight">Auto Replay</span>
        </label>
        
        <label className="flex items-center gap-1.5 cursor-pointer">
          <input 
            type="checkbox" 
            checked={autoTrade} 
            onChange={(e) => setAutoTrade(e.target.checked)}
            className="w-3.5 h-3.5 accent-tv-blue border-tv-border cursor-pointer"
          />
          <span className="text-[11px] font-bold text-tv-text uppercase tracking-tight">Auto Trade</span>
        </label>

        <div className="sep h-4" />

        <label className="flex items-center gap-1.5 cursor-pointer">
          <input 
            type="checkbox" 
            checked={showPartial} 
            onChange={(e) => setShowPartial(e.target.checked)}
            className="w-3.5 h-3.5 accent-tv-blue border-tv-border cursor-pointer"
          />
          <span className="text-[10px] font-bold text-tv-muted uppercase">Partial</span>
        </label>

        <label className="flex items-center gap-1.5 cursor-pointer">
          <input 
            type="checkbox" 
            checked={showFull} 
            onChange={(e) => setShowFull(e.target.checked)}
            className="w-3.5 h-3.5 accent-tv-blue border-tv-border cursor-pointer"
          />
          <span className="text-[10px] font-bold text-tv-muted uppercase">Full</span>
        </label>
      </div>
    </div>
  );
};

export default Toolbar;
