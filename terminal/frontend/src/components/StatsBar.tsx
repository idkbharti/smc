import React from 'react';

interface StatsBarProps {
  trades: number;
  wins: number;
  losses: number;
  winRate: string;
  pnl: string;
}

const StatsBar: React.FC<StatsBarProps> = ({ trades, wins, losses, winRate, pnl }) => {
  return (
    <div className="h-7 border-b border-tv-border bg-white flex items-center px-4 gap-6 text-[11px] text-tv-muted shadow-sm">
      <div className="flex gap-1.5 items-center">
        <span>Trades:</span>
        <strong className="text-tv-text">{trades}</strong>
      </div>
      <div className="flex gap-1.5 items-center">
        <span>Wins:</span>
        <strong className="text-tv-green">{wins}</strong>
      </div>
      <div className="flex gap-1.5 items-center">
        <span>Losses:</span>
        <strong className="text-tv-red">{losses}</strong>
      </div>
      <div className="flex gap-1.5 items-center">
        <span>Win Rate:</span>
        <strong className="text-tv-text">{winRate}</strong>
      </div>
      <div className="flex gap-1.5 items-center">
        <span>PnL (R):</span>
        <strong className={pnl.includes('-') ? 'text-tv-red' : 'text-tv-green'}>{pnl}</strong>
      </div>
    </div>
  );
};

export default StatsBar;
