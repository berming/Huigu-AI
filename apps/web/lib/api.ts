import axios from 'axios';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

// ── Types ─────────────────────────────────────────────────────────────────────

export interface StockQuote {
  symbol: string; name: string; price: number; change: number; change_pct: number;
  open: number; high: number; low: number; prev_close: number;
  volume: number; amount: number; turnover_rate?: number; pe_ratio?: number; market_cap?: number;
}
export interface KLineBar {
  date: string; open: number; high: number; low: number; close: number; volume: number; amount: number;
}
export interface KLineData { symbol: string; name: string; period: string; bars: KLineBar[]; }
export interface IndexQuote { symbol: string; name: string; price: number; change: number; change_pct: number; }
export interface MarketOverview { indices: IndexQuote[]; up_count: number; down_count: number; flat_count: number; }
export interface StockSearchResult { symbol: string; name: string; market: string; }

export type SentimentLabel = 'bullish' | 'bearish' | 'neutral';
export interface SentimentScore {
  bull_ratio: number; bear_ratio: number; neutral_ratio: number; total_posts: number; heat_score: number;
}
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

// ── API functions ─────────────────────────────────────────────────────────────

export const marketApi = {
  overview: () => apiClient.get<MarketOverview>('/api/market/overview').then(r => r.data),
  quote: (s: string) => apiClient.get<StockQuote>(`/api/market/quote/${s}`).then(r => r.data),
  kline: (s: string, period = 'D') => apiClient.get<KLineData>(`/api/market/kline/${s}`, { params: { period } }).then(r => r.data),
  search: (q: string) => apiClient.get<StockSearchResult[]>('/api/market/search', { params: { q } }).then(r => r.data),
  watchlistQuotes: (symbols: string[]) => apiClient.post<StockQuote[]>('/api/market/watchlist/quotes', symbols).then(r => r.data),
};

export const sentimentApi = {
  score: (sym: string, name: string) => apiClient.get<SentimentScore>(`/api/sentiment/${sym}/score`, { params: { name } }).then(r => r.data),
  posts: (sym: string, name: string, limit = 30) => apiClient.get<SocialPost[]>(`/api/sentiment/${sym}/posts`, { params: { name, limit } }).then(r => r.data),
  influencers: (sym: string, name: string) => apiClient.get<Influencer[]>(`/api/sentiment/${sym}/influencers`, { params: { name } }).then(r => r.data),
};

export const aiApi = {
  debate: (sym: string, name: string) =>
    apiClient.post<BullBearDebate>(`/api/ai/debate/${sym}`, {}, { params: { name } }).then(r => r.data),
  analyzeUrl: (sym: string, name: string) =>
    `${BASE_URL}/api/ai/analyze/${sym}?name=${encodeURIComponent(name)}`,
};
