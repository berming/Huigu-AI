'use client';
import { useState, useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { marketApi, StockSearchResult } from '@/lib/api';
import { useWatchlistStore } from '@/lib/store';

export function SearchBar() {
  const [q, setQ] = useState('');
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const { addStock } = useWatchlistStore();

  const { data: results } = useQuery({
    queryKey: ['search', q],
    queryFn: () => marketApi.search(q),
    enabled: q.length > 0,
    staleTime: 60_000,
  });

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  return (
    <div ref={ref} style={{ position: 'relative', width: 280 }}>
      <input
        value={q}
        onChange={e => { setQ(e.target.value); setOpen(true); }}
        onFocus={() => setOpen(true)}
        placeholder="搜索股票代码或名称..."
        style={{
          width: '100%', padding: '8px 14px', borderRadius: 8,
          background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)',
          color: 'var(--text-primary)', fontSize: 13, outline: 'none',
        }}
      />
      {open && results && results.length > 0 && (
        <div style={{
          position: 'absolute', top: '100%', left: 0, right: 0, marginTop: 4,
          background: 'var(--bg-card)', border: '1px solid var(--bg-border)',
          borderRadius: 8, zIndex: 100, maxHeight: 300, overflowY: 'auto',
        }}>
          {results.slice(0, 10).map((r: StockSearchResult) => (
            <button key={r.symbol} onClick={() => {
              addStock({ symbol: r.symbol, name: r.name });
              setQ(''); setOpen(false);
            }} style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              width: '100%', padding: '10px 14px', textAlign: 'left',
              borderBottom: '1px solid var(--bg-border)', transition: 'background 0.1s',
            }}
              onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-elevated)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
            >
              <div>
                <div style={{ fontWeight: 600, fontSize: 14 }}>{r.name}</div>
                <div style={{ color: 'var(--text-muted)', fontSize: 11 }}>{r.symbol} · {r.market}</div>
              </div>
              <span style={{ color: 'var(--brand-primary)', fontSize: 12 }}>+ 添加</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
