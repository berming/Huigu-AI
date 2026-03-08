/**
 * Watchlist store — persistent via AsyncStorage.
 *
 * Features:
 *  - Survives app restarts (AsyncStorage)
 *  - Per-stock price alerts (upper / lower targets)
 *  - Group labels ("自选" / "重点关注" / custom)
 *  - Manual ordering
 */
import { create } from 'zustand';
import AsyncStorage from '@react-native-async-storage/async-storage';

const STORAGE_KEY = '@huigu_watchlist_v2';

export interface PriceAlert {
  enabled: boolean;
  upperTarget?: number;   // 涨至此价提醒
  lowerTarget?: number;   // 跌至此价提醒
  upperTriggered: boolean;
  lowerTriggered: boolean;
}

export interface WatchedStock {
  symbol: string;
  name: string;
  addedAt: string;        // ISO timestamp
  group: string;          // "自选" | "重点关注" | custom
  alert: PriceAlert;
  note?: string;
}

interface WatchlistState {
  stocks: WatchedStock[];
  hydrated: boolean;

  isWatched: (symbol: string) => boolean;
  getStock: (symbol: string) => WatchedStock | undefined;
  symbols: () => string[];
  names: () => Record<string, string>;
  groups: () => string[];

  addStock: (symbol: string, name: string, group?: string) => void;
  removeStock: (symbol: string) => void;
  reorderStock: (symbol: string, direction: 'up' | 'down') => void;
  setNote: (symbol: string, note: string) => void;
  setGroup: (symbol: string, group: string) => void;

  setAlert: (symbol: string, alert: Partial<PriceAlert>) => void;
  resetAlertTriggers: (symbol: string) => void;
  markAlertTriggered: (symbol: string, side: 'upper' | 'lower') => void;

  hydrate: () => Promise<void>;
  _persist: () => Promise<void>;
}

const DEFAULT_STOCKS: WatchedStock[] = [
  { symbol: '000001', name: '平安银行', group: '自选', addedAt: new Date().toISOString(), alert: { enabled: false, upperTriggered: false, lowerTriggered: false } },
  { symbol: '600519', name: '贵州茅台', group: '重点关注', addedAt: new Date().toISOString(), alert: { enabled: false, upperTriggered: false, lowerTriggered: false } },
  { symbol: '000858', name: '五粮液', group: '自选', addedAt: new Date().toISOString(), alert: { enabled: false, upperTriggered: false, lowerTriggered: false } },
  { symbol: '601318', name: '中国平安', group: '自选', addedAt: new Date().toISOString(), alert: { enabled: false, upperTriggered: false, lowerTriggered: false } },
  { symbol: '300750', name: '宁德时代', group: '重点关注', addedAt: new Date().toISOString(), alert: { enabled: false, upperTriggered: false, lowerTriggered: false } },
  { symbol: '002594', name: '比亚迪', group: '自选', addedAt: new Date().toISOString(), alert: { enabled: false, upperTriggered: false, lowerTriggered: false } },
];

export const useWatchlistStore = create<WatchlistState>((set, get) => ({
  stocks: DEFAULT_STOCKS,
  hydrated: false,

  symbols: () => get().stocks.map(s => s.symbol),
  names: () => Object.fromEntries(get().stocks.map(s => [s.symbol, s.name])),
  groups: () => {
    const all = get().stocks.map(s => s.group);
    return ['全部', ...Array.from(new Set(all))];
  },

  isWatched: (symbol) => get().stocks.some(s => s.symbol === symbol),
  getStock: (symbol) => get().stocks.find(s => s.symbol === symbol),

  addStock: (symbol, name, group = '自选') => {
    if (get().isWatched(symbol)) return;
    const stock: WatchedStock = {
      symbol, name, group,
      addedAt: new Date().toISOString(),
      alert: { enabled: false, upperTriggered: false, lowerTriggered: false },
    };
    set(state => ({ stocks: [...state.stocks, stock] }));
    get()._persist();
  },

  removeStock: (symbol) => {
    set(state => ({ stocks: state.stocks.filter(s => s.symbol !== symbol) }));
    get()._persist();
  },

  reorderStock: (symbol, direction) => {
    set(state => {
      const stocks = [...state.stocks];
      const idx = stocks.findIndex(s => s.symbol === symbol);
      if (idx === -1) return state;
      const target = direction === 'up' ? idx - 1 : idx + 1;
      if (target < 0 || target >= stocks.length) return state;
      [stocks[idx], stocks[target]] = [stocks[target], stocks[idx]];
      return { stocks };
    });
    get()._persist();
  },

  setNote: (symbol, note) => {
    set(state => ({
      stocks: state.stocks.map(s => s.symbol === symbol ? { ...s, note } : s),
    }));
    get()._persist();
  },

  setGroup: (symbol, group) => {
    set(state => ({
      stocks: state.stocks.map(s => s.symbol === symbol ? { ...s, group } : s),
    }));
    get()._persist();
  },

  setAlert: (symbol, partial) => {
    set(state => ({
      stocks: state.stocks.map(s =>
        s.symbol === symbol ? { ...s, alert: { ...s.alert, ...partial } } : s
      ),
    }));
    get()._persist();
  },

  resetAlertTriggers: (symbol) => {
    set(state => ({
      stocks: state.stocks.map(s =>
        s.symbol === symbol
          ? { ...s, alert: { ...s.alert, upperTriggered: false, lowerTriggered: false } }
          : s
      ),
    }));
    get()._persist();
  },

  markAlertTriggered: (symbol, side) => {
    set(state => ({
      stocks: state.stocks.map(s =>
        s.symbol === symbol
          ? {
              ...s,
              alert: {
                ...s.alert,
                upperTriggered: side === 'upper' ? true : s.alert.upperTriggered,
                lowerTriggered: side === 'lower' ? true : s.alert.lowerTriggered,
              },
            }
          : s
      ),
    }));
    get()._persist();
  },

  hydrate: async () => {
    try {
      const raw = await AsyncStorage.getItem(STORAGE_KEY);
      if (raw) {
        const saved: WatchedStock[] = JSON.parse(raw);
        if (Array.isArray(saved) && saved.length > 0) {
          set({ stocks: saved, hydrated: true });
          return;
        }
      }
    } catch (e) {
      console.warn('[Watchlist] hydrate failed:', e);
    }
    set({ hydrated: true });
  },

  _persist: async () => {
    try {
      await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(get().stocks));
    } catch (e) {
      console.warn('[Watchlist] persist failed:', e);
    }
  },
}));
