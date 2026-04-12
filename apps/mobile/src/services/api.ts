/**
 * Data service for the mobile app — standalone, no backend required.
 * All data is generated locally via the mock module.
 * To connect to a real backend later, replace mock calls with axios calls.
 */
import {
  getMarketOverview,
  getStockQuote,
  getBatchQuotes,
  getKline,
  searchStocks,
  getSentimentScore,
  getSocialPosts,
  getHeatTimeline,
  getInfluencers,
  getMockDebate,
  getMockAnalysis,
} from './mock';

// ── Types ─────────────────────────────────────────────────────────────────────

export interface StockQuote {
  symbol: string; name: string; price: number; change: number; change_pct: number;
  open: number; high: number; low: number; prev_close: number;
  volume: number; amount: number; turnover_rate?: number; pe_ratio?: number; market_cap?: number;
}
export interface KLineBar { date: string; open: number; high: number; low: number; close: number; volume: number; amount: number; }
export interface KLineData { symbol: string; name: string; period: string; bars: KLineBar[]; }
export interface IndexQuote { symbol: string; name: string; price: number; change: number; change_pct: number; }
export interface MarketOverview { indices: IndexQuote[]; up_count: number; down_count: number; flat_count: number; }
export interface StockSearchResult { symbol: string; name: string; market: string; }
export interface SentimentScore { bull_ratio: number; bear_ratio: number; neutral_ratio: number; total_posts: number; heat_score: number; }
export interface HeatPoint { time: string; count: number; sentiment: number; }
export type SentimentLabel = 'bullish' | 'bearish' | 'neutral';
export interface SocialPost {
  id: string; platform: string; author: string; avatar_url?: string; content: string;
  published_at: string; likes: number; comments: number;
  sentiment: SentimentLabel; sentiment_score: number; is_influencer: boolean;
}
export interface Influencer {
  id: string; name: string; platform: string; avatar_url?: string; followers: number;
  win_rate: number; avg_return: number; total_calls: number;
  latest_view: string; latest_view_sentiment: SentimentLabel;
}
export interface DebateArgument { point: string; evidence: string; strength: number; }
export interface BullBearDebate {
  symbol: string; name: string; generated_at: string; bull_ratio: number;
  bull_arguments: DebateArgument[]; bear_arguments: DebateArgument[];
  key_risks: string[]; key_opportunities: string[]; ai_summary: string;
}
export interface AlertTarget { symbol: string; name: string; upper_target?: number; lower_target?: number; }
export interface AlertResult {
  symbol: string; name: string; current_price: number;
  upper_triggered: boolean; lower_triggered: boolean;
  upper_target?: number; lower_target?: number;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function delay<T>(value: T, ms = 120): Promise<T> {
  return new Promise(resolve => setTimeout(() => resolve(value), ms));
}

// ── API (standalone mock implementation) ─────────────────────────────────────

export const marketApi = {
  overview: () => delay(getMarketOverview() as MarketOverview),
  quote: (symbol: string) => {
    const q = getStockQuote(symbol);
    if (!q) return Promise.reject(new Error(`Unknown symbol: ${symbol}`));
    return delay(q as StockQuote);
  },
  kline:          (symbol: string, period = 'D') => delay(getKline(symbol, period) as KLineData),
  search:         (q: string)                    => delay(searchStocks(q) as StockSearchResult[]),
  watchlistQuotes:(symbols: string[])            => delay(getBatchQuotes(symbols) as StockQuote[]),
};

export const sentimentApi = {
  score:       (symbol: string, _name: string)            => delay(getSentimentScore(symbol) as SentimentScore),
  posts:       (symbol: string, name: string, limit = 30) => delay(getSocialPosts(symbol, name, limit) as SocialPost[]),
  heat:        (symbol: string)                           => delay(getHeatTimeline(symbol) as HeatPoint[]),
  influencers: (symbol: string, name: string)             => delay(getInfluencers(symbol, name) as Influencer[]),
};

export const alertApi = {
  check: (targets: AlertTarget[]): Promise<AlertResult[]> => {
    const results = targets.map(t => {
      const q     = getStockQuote(t.symbol);
      const price = q?.price ?? 0;
      return {
        symbol:           t.symbol,
        name:             t.name,
        current_price:    price,
        upper_triggered:  t.upper_target !== undefined && price >= t.upper_target,
        lower_triggered:  t.lower_target !== undefined && price <= t.lower_target,
        upper_target:     t.upper_target,
        lower_target:     t.lower_target,
      };
    });
    return delay(results);
  },
};

export const aiApi = {
  debate:       (symbol: string, name: string) => delay(getMockDebate(symbol, name) as BullBearDebate, 800),
  summarizePost: (content: string) => {
    const snippet = content.slice(0, 40);
    return delay({ summary: `该帖子分析了相关股票的投资逻辑：${snippet}…` }, 300);
  },
  analyze: (symbol: string, name: string) => delay(getMockAnalysis(symbol, name), 600),
};
