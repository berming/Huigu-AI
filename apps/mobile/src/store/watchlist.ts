import { create } from 'zustand';

interface WatchlistState {
  symbols: string[];
  names: Record<string, string>;
  addStock: (symbol: string, name: string) => void;
  removeStock: (symbol: string) => void;
  isWatched: (symbol: string) => boolean;
}

// Default watchlist with popular A-shares
const DEFAULT_WATCHLIST = [
  { symbol: '000001', name: '平安银行' },
  { symbol: '600519', name: '贵州茅台' },
  { symbol: '000858', name: '五粮液' },
  { symbol: '601318', name: '中国平安' },
  { symbol: '300750', name: '宁德时代' },
  { symbol: '002594', name: '比亚迪' },
];

export const useWatchlistStore = create<WatchlistState>((set, get) => ({
  symbols: DEFAULT_WATCHLIST.map(s => s.symbol),
  names: Object.fromEntries(DEFAULT_WATCHLIST.map(s => [s.symbol, s.name])),

  addStock: (symbol, name) => set(state => ({
    symbols: state.symbols.includes(symbol) ? state.symbols : [...state.symbols, symbol],
    names: { ...state.names, [symbol]: name },
  })),

  removeStock: (symbol) => set(state => ({
    symbols: state.symbols.filter(s => s !== symbol),
  })),

  isWatched: (symbol) => get().symbols.includes(symbol),
}));
