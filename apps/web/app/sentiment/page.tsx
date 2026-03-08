'use client';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { sentimentApi } from '@/lib/api';
import { useWatchlistStore } from '@/lib/store';
import { SentimentGauge } from '@/components/sentiment/SentimentGauge';
import { PostCard } from '@/components/sentiment/PostCard';
import { LoadingSpinner } from '@/components/common/LoadingSpinner';

type SubTab = 'posts' | 'influencers';

const SENTIMENT_COLOR: Record<string, string> = {
  bullish: 'var(--market-up)', bearish: 'var(--market-down)', neutral: 'var(--market-flat)',
};
const SENTIMENT_LABEL: Record<string, string> = { bullish: '偏多', bearish: '偏空', neutral: '中性' };

export default function SentimentPage() {
  const { stocks, names } = useWatchlistStore();
  const [selectedSymbol, setSelectedSymbol] = useState(stocks[0]?.symbol ?? '600519');
  const selectedName = names[selectedSymbol] ?? selectedSymbol;
  const [subTab, setSubTab] = useState<SubTab>('posts');

  const { data: score, isLoading: scoreLoading } = useQuery({
    queryKey: ['sentiment-score', selectedSymbol],
    queryFn: () => sentimentApi.score(selectedSymbol, selectedName),
    refetchInterval: 60_000,
  });

  const { data: posts, isLoading: postsLoading } = useQuery({
    queryKey: ['posts', selectedSymbol],
    queryFn: () => sentimentApi.posts(selectedSymbol, selectedName, 30),
    enabled: subTab === 'posts',
  });

  const { data: influencers } = useQuery({
    queryKey: ['influencers', selectedSymbol],
    queryFn: () => sentimentApi.influencers(selectedSymbol, selectedName),
    enabled: subTab === 'influencers',
  });

  return (
    <div style={{ display: 'flex', height: '100%' }}>
      {/* Left panel: stock selector + gauge */}
      <div style={{
        width: 320, borderRight: '1px solid var(--bg-border)',
        background: 'var(--bg-secondary)', display: 'flex', flexDirection: 'column',
        flexShrink: 0,
      }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--bg-border)' }}>
          <h1 style={{ fontSize: 18, fontWeight: 800, marginBottom: 2 }}>社区热议</h1>
          <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>股民情绪实时监控</div>
        </div>

        {/* Stock list */}
        <div style={{ overflowY: 'auto', flex: 1 }}>
          {stocks.map(s => (
            <button key={s.symbol} onClick={() => setSelectedSymbol(s.symbol)} style={{
              display: 'block', width: '100%', padding: '12px 20px', textAlign: 'left',
              background: s.symbol === selectedSymbol ? 'rgba(240,180,41,0.1)' : 'transparent',
              borderLeft: `3px solid ${s.symbol === selectedSymbol ? 'var(--brand-primary)' : 'transparent'}`,
              borderBottom: '1px solid var(--bg-border)',
              transition: 'all 0.15s',
            }}>
              <div style={{ fontWeight: 600, fontSize: 14, color: s.symbol === selectedSymbol ? 'var(--brand-primary)' : 'var(--text-primary)' }}>
                {s.name}
              </div>
              <div style={{ color: 'var(--text-muted)', fontSize: 11, marginTop: 2 }}>{s.symbol}</div>
            </button>
          ))}
        </div>

        {/* Gauge */}
        {score && (
          <div style={{ padding: 16, borderTop: '1px solid var(--bg-border)' }}>
            <SentimentGauge score={score} />
          </div>
        )}
        {scoreLoading && <LoadingSpinner text="加载情绪..." />}
      </div>

      {/* Right panel: posts / influencers */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* Sub-tabs */}
        <div style={{
          display: 'flex', gap: 8, padding: '12px 20px',
          background: 'var(--bg-secondary)', borderBottom: '1px solid var(--bg-border)',
        }}>
          {(['posts', 'influencers'] as SubTab[]).map(tab => (
            <button key={tab} onClick={() => setSubTab(tab)} style={{
              padding: '6px 16px', borderRadius: 999, fontSize: 13,
              background: subTab === tab ? 'rgba(240,180,41,0.15)' : 'var(--bg-elevated)',
              color: subTab === tab ? 'var(--brand-primary)' : 'var(--text-secondary)',
              fontWeight: subTab === tab ? 600 : 400,
              border: `1px solid ${subTab === tab ? 'var(--brand-primary)' : 'var(--bg-border)'}`,
            }}>
              {tab === 'posts' ? '最新讨论' : '达人榜'}
            </button>
          ))}
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: 20 }}>
          {subTab === 'posts' && (
            postsLoading ? <LoadingSpinner text="加载帖子..." /> :
            posts?.map(p => <PostCard key={p.id} post={p} />) ?? null
          )}
          {subTab === 'influencers' && influencers?.map((inf, i) => (
            <div key={inf.id} style={{
              background: 'var(--bg-card)', borderRadius: 10,
              border: '1px solid var(--bg-border)', padding: 16, marginBottom: 10,
              display: 'flex', alignItems: 'center', gap: 14,
            }}>
              <div style={{
                width: 32, height: 32, borderRadius: '50%', background: 'var(--bg-elevated)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontWeight: 700, color: 'var(--brand-primary)', fontSize: 14, flexShrink: 0,
              }}>#{i + 1}</div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 700, fontSize: 14 }}>{inf.name}</div>
                <div style={{ color: 'var(--text-muted)', fontSize: 11, marginTop: 2 }}>
                  {inf.platform} · {(inf.followers / 1e4).toFixed(1)}w粉丝
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ color: 'var(--market-up)', fontWeight: 700, fontSize: 16 }}>
                  {(inf.win_rate * 100).toFixed(0)}%
                </div>
                <div style={{ color: 'var(--text-muted)', fontSize: 11 }}>胜率</div>
              </div>
              <div style={{
                padding: '4px 12px', borderRadius: 999, fontSize: 12, fontWeight: 600,
                color: SENTIMENT_COLOR[inf.latest_view_sentiment],
                background: SENTIMENT_COLOR[inf.latest_view_sentiment] + '20',
              }}>
                {SENTIMENT_LABEL[inf.latest_view_sentiment]}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
