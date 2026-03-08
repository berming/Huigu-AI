'use client';
import { SentimentScore } from '@/lib/api';

export function SentimentGauge({ score }: { score: SentimentScore }) {
  const { bull_ratio, bear_ratio, neutral_ratio, total_posts, heat_score } = score;

  return (
    <div style={{
      background: 'var(--bg-card)', borderRadius: 12,
      border: '1px solid var(--bg-border)', padding: 20, marginBottom: 16,
    }}>
      {/* Heat score */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
        <div>
          <div style={{ color: 'var(--text-secondary)', fontSize: 12, marginBottom: 4 }}>市场情绪热度</div>
          <div style={{ fontSize: 36, fontWeight: 800, color: 'var(--brand-primary)' }}>
            {heat_score.toFixed(0)}
          </div>
          <div style={{ color: 'var(--text-muted)', fontSize: 11 }}>共 {total_posts} 条讨论</div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>综合情绪</div>
          <div style={{
            padding: '4px 14px', borderRadius: 999, fontWeight: 700, fontSize: 14,
            background: bull_ratio > bear_ratio ? 'var(--market-up-light)' : 'var(--market-down-light)',
            color: bull_ratio > bear_ratio ? 'var(--market-up)' : 'var(--market-down)',
          }}>
            {bull_ratio > bear_ratio ? '📈 偏多' : '📉 偏空'}
          </div>
        </div>
      </div>

      {/* Bull/Bear bar */}
      <div style={{ display: 'flex', gap: 4, height: 8, borderRadius: 4, overflow: 'hidden', marginBottom: 10 }}>
        <div style={{ flex: bull_ratio, background: 'var(--market-up)', borderRadius: '4px 0 0 4px' }} />
        <div style={{ flex: neutral_ratio, background: 'var(--market-flat)' }} />
        <div style={{ flex: bear_ratio, background: 'var(--market-down)', borderRadius: '0 4px 4px 0' }} />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
        <span style={{ color: 'var(--market-up)' }}>多 {(bull_ratio * 100).toFixed(0)}%</span>
        <span style={{ color: 'var(--market-flat)' }}>中性 {(neutral_ratio * 100).toFixed(0)}%</span>
        <span style={{ color: 'var(--market-down)' }}>空 {(bear_ratio * 100).toFixed(0)}%</span>
      </div>
    </div>
  );
}
