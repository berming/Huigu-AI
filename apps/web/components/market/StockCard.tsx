'use client';
import { StockQuote } from '@/lib/api';

interface Props {
  quote: StockQuote;
  onClick: () => void;
  onRemove: () => void;
}

function fmt(n: number) { return n >= 1e8 ? (n / 1e8).toFixed(2) + '亿' : (n / 1e4).toFixed(0) + '万'; }

export function StockCard({ quote: q, onClick, onRemove }: Props) {
  const up = q.change_pct >= 0;
  const color = q.change_pct === 0 ? 'var(--market-flat)' : up ? 'var(--market-up)' : 'var(--market-down)';
  const bg = q.change_pct === 0 ? 'transparent' : up ? 'var(--market-up-light)' : 'var(--market-down-light)';

  return (
    <div onClick={onClick} style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '14px 20px', background: 'var(--bg-card)',
      borderBottom: '1px solid var(--bg-border)', cursor: 'pointer',
      transition: 'background 0.15s',
    }}
      onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-elevated)')}
      onMouseLeave={e => (e.currentTarget.style.background = 'var(--bg-card)')}
    >
      {/* Left: name + meta */}
      <div style={{ flex: 1 }}>
        <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 4 }}>{q.name}</div>
        <div style={{ color: 'var(--text-muted)', fontSize: 11 }}>
          {q.symbol} · 量 {fmt(q.volume)} · 额 {fmt(q.amount)}
        </div>
      </div>

      {/* Right: price + pct */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 20, fontWeight: 700, color }}>{q.price.toFixed(2)}</div>
          <div style={{ color: 'var(--text-muted)', fontSize: 11 }}>
            {q.change >= 0 ? '+' : ''}{q.change.toFixed(2)}
          </div>
        </div>
        <div style={{
          minWidth: 70, padding: '6px 12px', borderRadius: 8,
          background: bg, color, fontWeight: 700, fontSize: 15, textAlign: 'center',
        }}>
          {up ? '+' : ''}{q.change_pct.toFixed(2)}%
        </div>
        <button onClick={e => { e.stopPropagation(); onRemove(); }} style={{
          color: 'var(--text-muted)', fontSize: 18, padding: '4px 8px', borderRadius: 4,
          opacity: 0.6,
        }}
          onMouseEnter={e => (e.currentTarget.style.opacity = '1')}
          onMouseLeave={e => (e.currentTarget.style.opacity = '0.6')}
        >×</button>
      </div>
    </div>
  );
}
