'use client';
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface WatchlistStock { symbol: string; name: string; }

interface WatchlistState {
  stocks: WatchlistStock[];
  addStock: (s: WatchlistStock) => void;
  removeStock: (symbol: string) => void;
  symbols: () => string[];
  names: Record<string, string>;
}

export const useWatchlistStore = create<WatchlistState>()(
  persist(
    (set, get) => ({
      stocks: [
        { symbol: '600519', name: '贵州茅台' },
        { symbol: '000858', name: '五粮液' },
        { symbol: '300750', name: '宁德时代' },
      ],
      names: { '600519': '贵州茅台', '000858': '五粮液', '300750': '宁德时代' },
      addStock: (s) => set(st => {
        if (st.stocks.find(x => x.symbol === s.symbol)) return st;
        const stocks = [...st.stocks, s];
        return { stocks, names: { ...st.names, [s.symbol]: s.name } };
      }),
      removeStock: (symbol) => set(st => ({
        stocks: st.stocks.filter(x => x.symbol !== symbol),
      })),
      symbols: () => get().stocks.map(s => s.symbol),
    }),
    { name: 'huigu-watchlist' }
  )
);
