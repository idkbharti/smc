import React, { useState, useEffect } from 'react';
import { User } from 'lucide-react';
import axios from 'axios';

interface AccountInfo {
  name: string;
  server: string;
  balance: number;
  equity: number;
  currency: string;
  trade_mode: number;
}

interface TopBarProps {
  symbol: string;
  setSymbol: (s: string) => void;
  timeframe: number;
  setTimeframe: (tf: number) => void;
  watchlist: string[];
}

const TopBar: React.FC<TopBarProps> = ({ symbol, setSymbol, timeframe, setTimeframe, watchlist }) => {
  const [account, setAccount] = useState<AccountInfo | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    axios.get('http://127.0.0.1:8085/api/init').then(res => {
      if (res.data.account) {
        setAccount(res.data.account);
        setConnected(true);
      }
    }).catch(err => {
      console.error("Init failed", err);
      setConnected(false);
    });
  }, []);

  return (
    <div className="h-10 border-b border-tv-border bg-white flex items-center px-3 gap-2">
      <div className="flex items-center gap-2 mr-2">
        <span className="font-bold text-tv-blue text-sm tracking-tight">⚡ SMC Terminal</span>
        <div className={`w-2 h-2 rounded-full ${connected ? 'bg-tv-green shadow-[0_0_5px_rgba(38,166,154,0.5)]' : 'bg-tv-red animate-pulse'}`} title={connected ? 'Connected to Backend' : 'Disconnected'} />
      </div>

      <div className="sep" />

      {/* Symbol Select */}
      <span className="text-[11px] text-tv-muted uppercase font-semibold ml-1">Symbol</span>
      <select
        className="tv-select w-28"
        value={symbol}
        onChange={(e) => setSymbol(e.target.value)}
      >
        {watchlist.map(s => <option key={s} value={s}>{s}</option>)}
      </select>

      <div className="sep" />

      {/* TF Select */}
      <span className="text-[11px] text-tv-muted uppercase font-semibold ml-1">TF</span>
      <select
        className="tv-select w-16"
        value={timeframe}
        onChange={(e) => setTimeframe(Number(e.target.value))}
      >
        <option value={1}>1m</option>
        <option value={5}>5m</option>
        <option value={15}>15m</option>
        <option value={60}>1h</option>
        <option value={240}>4h</option>
      </select>

      <div className="sep" />

      {/* Account Info */}
      <div className="ml-auto flex items-center gap-3 relative group">
        <div className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase text-white ${account?.trade_mode === 0 ? 'bg-orange-500' : 'bg-tv-green'}`}>
          {account?.trade_mode === 0 ? 'Demo' : 'Real'}
        </div>

        <div className="w-7 h-7 bg-tv-blue rounded-full flex items-center justify-center text-white cursor-pointer">
          <User size={16} />
        </div>

        {/* Hover Dropdown */}
        <div className="absolute top-10 right-0 w-56 bg-white border border-tv-border rounded-lg shadow-xl p-3 z-50 hidden group-hover:block translate-y-[-5px] group-hover:translate-y-0 transition-transform">
          <div className="flex justify-between text-[11px] mb-2">
            <span className="text-tv-muted">Name:</span>
            <span className="font-bold">{account?.name || 'Loading...'}</span>
          </div>
          <div className="flex justify-between text-[11px] mb-2">
            <span className="text-tv-muted">Server:</span>
            <span className="font-bold">{account?.server || 'Loading...'}</span>
          </div>
          <div className="h-px bg-tv-border my-2" />
          <div className="flex justify-between text-[11px] mb-2">
            <span className="text-tv-muted">Balance:</span>
            <span className="font-bold text-tv-blue">{account?.balance.toFixed(2)}</span>
          </div>
          <div className="flex justify-between text-[11px] mb-2">
            <span className="text-tv-muted">Equity:</span>
            <span className="font-bold">{account?.equity.toFixed(2)}</span>
          </div>
          <div className="flex justify-between text-[11px]">
            <span className="text-tv-muted">Currency:</span>
            <span className="font-bold uppercase">{account?.currency}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TopBar;
