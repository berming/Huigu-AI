/**
 * Market store — quotes, history and alert evaluation.
 *
 * New capabilities:
 *  - Tracks previous price per symbol for flash animation (up / down / flat)
 *  - Stores mini sparkline data (last 20 prices) per symbol
 *  - Evaluates price alerts against current quotes
 */
import { create } from 'zustand';
import { StockQuote, MarketOverview } from '../services/api';
import { useWatchlistStore } from './watchlist';

export type PriceDirection = 'up' | 'down' | 'flat';

interface MarketState {
  overview: MarketOverview | null;
  quotes: Record<string, StockQuote>;
  prevPrices: Record<string, number>;         // price before latest update
  sparklines: Record<string, number[]>;       // last 20 close prices per symbol
  flashDir: Record<string, PriceDirection>;   // animated flash direction

  setOverview: (overview: MarketOverview) => void;
  setQuote: (symbol: string, quote: StockQuote) => void;
  setQuotes: (quotes: StockQuote[]) => void;
}

const MAX_SPARKLINE = 20;

function evaluateAlerts(symbol: string, price: number) {
  const { getStock, markAlertTriggered } = useWatchlistStore.getState();
  const stock = getStock(symbol);
  if (!stock?.alert.enabled) return;

  const { upperTarget, lowerTarget, upperTriggered, lowerTriggered } = stock.alert;
  if (upperTarget && !upperTriggered && price >= upperTarget) {
    markAlertTriggered(symbol, 'upper');
    console.log(`[Alert] ${symbol} 突破目标价 ${upperTarget}`);
  }
  if (lowerTarget && !lowerTriggered && price <= lowerTarget) {
    markAlertTriggered(symbol, 'lower');
    console.log(`[Alert] ${symbol} 跌破预警价 ${lowerTarget}`);
  }
}

export const useMarketStore = create<MarketState>((set, get) => ({
  overview: null,
  quotes: {},
  prevPrices: {},
  sparklines: {},
  flashDir: {},

  setOverview: (overview) => set({ overview }),

  setQuote: (symbol, quote) => {
    const prev = get().quotes[symbol];
    const prevPrice = prev?.price ?? quote.price;
    const dir: PriceDirection = quote.price > prevPrice ? 'up' : quote.price < prevPrice ? 'down' : 'flat';

    const spark = get().sparklines[symbol] ?? [];
    const newSpark = [...spark, quote.price].slice(-MAX_SPARKLINE);

    evaluateAlerts(symbol, quote.price);

    set(state => ({
      quotes: { ...state.quotes, [symbol]: quote },
      prevPrices: { ...state.prevPrices, [symbol]: prevPrice },
      sparklines: { ...state.sparklines, [symbol]: newSpark },
      flashDir: { ...state.flashDir, [symbol]: dir },
    }));

    // Clear flash after 800ms
    setTimeout(() => {
      set(state => ({
        flashDir: { ...state.flashDir, [symbol]: 'flat' },
      }));
    }, 800);
  },

  setQuotes: (quotes) => {
    quotes.forEach(q => get().setQuote(q.symbol, q));
  },
}));
