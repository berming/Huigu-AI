import { create } from 'zustand';
import { StockQuote, MarketOverview } from '../services/api';

interface MarketState {
  overview: MarketOverview | null;
  quotes: Record<string, StockQuote>;
  setOverview: (overview: MarketOverview) => void;
  setQuote: (symbol: string, quote: StockQuote) => void;
  setQuotes: (quotes: StockQuote[]) => void;
}

export const useMarketStore = create<MarketState>((set) => ({
  overview: null,
  quotes: {},

  setOverview: (overview) => set({ overview }),

  setQuote: (symbol, quote) => set(state => ({
    quotes: { ...state.quotes, [symbol]: quote },
  })),

  setQuotes: (quotes) => set(state => ({
    quotes: {
      ...state.quotes,
      ...Object.fromEntries(quotes.map(q => [q.symbol, q])),
    },
  })),
}));
