'use client';
import { IndexQuote } from '@/lib/api';

function pct(v: number) {
  const up = v >= 0;
  return <span style={{ color: up ? 'var(--market-up)' : 'var(--market-down)', fontWeight: 600, fontSize: 13 }}>
    {up ? '+' : ''}{v.toFixed(2)}%
  </span>;
}

export function IndexBar({ indices }: { indices: IndexQuote[] }) {
  return (
    <div style={{
      display: 'flex', gap: 0, background: 'var(--bg-secondary)',
      borderBottom: '1px solid var(--bg-border)', overflowX: 'auto',
    }}>
      {indices.map(idx => (
        <div key={idx.symbol} style={{
          padding: '12px 20px', minWidth: 140, borderRight: '1px solid var(--bg-border)',
          flexShrink: 0,
        }}>
          <div style={{ color: 'var(--text-muted)', fontSize: 11, marginBottom: 4 }}>{idx.name}</div>
          <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 2 }}>
            {idx.price.toFixed(2)}
          </div>
          {pct(idx.change_pct)}
        </div>
      ))}
    </div>
  );
}
