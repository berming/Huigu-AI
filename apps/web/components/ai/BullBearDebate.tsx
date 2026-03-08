'use client';
import { BullBearDebate, DebateArgument } from '@/lib/api';

function ArgList({ args, side }: { args: DebateArgument[]; side: 'bull' | 'bear' }) {
  const color = side === 'bull' ? 'var(--market-up)' : 'var(--market-down)';
  return (
    <div style={{ flex: 1 }}>
      <div style={{ color, fontWeight: 700, fontSize: 13, marginBottom: 10 }}>
        {side === 'bull' ? '📈 多方论点' : '📉 空方论点'}
      </div>
      {args.map((a, i) => (
        <div key={i} style={{
          background: 'var(--bg-elevated)', borderRadius: 8,
          border: `1px solid ${color}30`, padding: 12, marginBottom: 8,
        }}>
          <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>{a.point}</div>
          <div style={{ color: 'var(--text-secondary)', fontSize: 12, lineHeight: 1.6 }}>{a.evidence}</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 8 }}>
            <div style={{
              height: 4, borderRadius: 2,
              width: `${a.strength}%`, background: color, maxWidth: 120,
            }} />
            <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>信心 {a.strength}%</span>
          </div>
        </div>
      ))}
    </div>
  );
}

export function BullBearDebateCard({ debate }: { debate: BullBearDebate }) {
  return (
    <div style={{ background: 'var(--bg-card)', borderRadius: 12, border: '1px solid var(--bg-border)', padding: 20 }}>
      {/* Header ratio */}
      <div style={{ display: 'flex', gap: 4, height: 6, borderRadius: 3, overflow: 'hidden', marginBottom: 16 }}>
        <div style={{ flex: debate.bull_ratio, background: 'var(--market-up)' }} />
        <div style={{ flex: 1 - debate.bull_ratio, background: 'var(--market-down)' }} />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 20 }}>
        <span style={{ color: 'var(--market-up)' }}>多方 {(debate.bull_ratio * 100).toFixed(0)}%</span>
        <span style={{ color: 'var(--market-down)' }}>空方 {((1 - debate.bull_ratio) * 100).toFixed(0)}%</span>
      </div>

      {/* Arguments */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 20 }}>
        <ArgList args={debate.bull_arguments} side="bull" />
        <ArgList args={debate.bear_arguments} side="bear" />
      </div>

      {/* AI Summary */}
      <div style={{
        background: 'rgba(168,85,247,0.08)', border: '1px solid rgba(168,85,247,0.3)',
        borderRadius: 8, padding: 14,
      }}>
        <div style={{ color: 'var(--ai-purple)', fontSize: 12, fontWeight: 600, marginBottom: 8 }}>
          ⚡ Claude AI 综合点评
        </div>
        <p style={{ color: 'var(--text-secondary)', fontSize: 13, lineHeight: 1.7 }}>{debate.ai_summary}</p>
      </div>
    </div>
  );
}
