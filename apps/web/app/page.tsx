'use client';
import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { marketApi, StockQuote } from '@/lib/api';
import { useWatchlistStore } from '@/lib/store';
import { IndexBar } from '@/components/market/IndexBar';
import { StockCard } from '@/components/market/StockCard';
import { SearchBar } from '@/components/market/SearchBar';
import { LoadingSpinner } from '@/components/common/LoadingSpinner';

export default function MarketPage() {
  const { stocks, symbols, removeStock, names } = useWatchlistStore();
  const symList = symbols();

  const { data: overview } = useQuery({
    queryKey: ['overview'],
    queryFn: marketApi.overview,
    refetchInterval: 30_000,
  });

  const { data: quotes, isLoading } = useQuery({
    queryKey: ['watchlist', symList.join()],
    queryFn: () => marketApi.watchlistQuotes(symList),
    enabled: symList.length > 0,
    refetchInterval: 10_000,
  });

  const quoteMap: Record<string, StockQuote> = {};
  quotes?.forEach(q => { quoteMap[q.symbol] = q; });

  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const selectedQuote = selectedSymbol ? quoteMap[selectedSymbol] : null;

  return (
    <div style={{ display: 'flex', height: '100%' }}>
      {/* Main list */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* Header */}
        <div style={{
          padding: '16px 24px', background: 'var(--bg-secondary)',
          borderBottom: '1px solid var(--bg-border)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <div>
            <h1 style={{ fontSize: 20, fontWeight: 800, marginBottom: 2 }}>行情中心</h1>
            <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>自选股实时行情</div>
          </div>
          <SearchBar />
        </div>

        {/* Index bar */}
        {overview && <IndexBar indices={overview.indices} />}

        {/* Market stats */}
        {overview && (
          <div style={{
            display: 'flex', gap: 24, padding: '10px 24px',
            background: 'var(--bg-secondary)', borderBottom: '1px solid var(--bg-border)',
            fontSize: 13,
          }}>
            <span>📈 <span style={{ color: 'var(--market-up)', fontWeight: 600 }}>{overview.up_count}</span> 涨</span>
            <span>📉 <span style={{ color: 'var(--market-down)', fontWeight: 600 }}>{overview.down_count}</span> 跌</span>
            <span>➖ <span style={{ color: 'var(--market-flat)', fontWeight: 600 }}>{overview.flat_count}</span> 平</span>
          </div>
        )}

        {/* Watchlist */}
        <div style={{ flex: 1, overflowY: 'auto' }}>
          <div style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            padding: '12px 24px', borderBottom: '1px solid var(--bg-border)',
          }}>
            <span style={{ fontWeight: 700, fontSize: 14 }}>我的自选 ({stocks.length})</span>
          </div>

          {isLoading && symList.length > 0 ? (
            <LoadingSpinner text="加载行情..." />
          ) : symList.length === 0 ? (
            <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
              <div style={{ fontSize: 32, marginBottom: 12 }}>📊</div>
              <div style={{ marginBottom: 8 }}>暂无自选股</div>
              <div style={{ fontSize: 12 }}>使用右上角搜索框添加股票</div>
            </div>
          ) : (
            symList.map(sym => {
              const q = quoteMap[sym];
              if (!q) return null;
              return (
                <StockCard
                  key={sym}
                  quote={q}
                  onClick={() => setSelectedSymbol(sym === selectedSymbol ? null : sym)}
                  onRemove={() => removeStock(sym)}
                />
              );
            })
          )}
        </div>
      </div>

      {/* Detail panel */}
      {selectedQuote && (
        <div style={{
          width: 360, borderLeft: '1px solid var(--bg-border)',
          background: 'var(--bg-secondary)', overflow: 'auto', flexShrink: 0,
        }}>
          <div style={{ padding: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
              <div>
                <div style={{ fontSize: 18, fontWeight: 800 }}>{selectedQuote.name}</div>
                <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>{selectedQuote.symbol}</div>
              </div>
              <button onClick={() => setSelectedSymbol(null)} style={{ color: 'var(--text-muted)', fontSize: 20 }}>×</button>
            </div>

            <div style={{ fontSize: 36, fontWeight: 800, marginBottom: 4, color: selectedQuote.change_pct >= 0 ? 'var(--market-up)' : 'var(--market-down)' }}>
              {selectedQuote.price.toFixed(2)}
            </div>
            <div style={{ color: selectedQuote.change_pct >= 0 ? 'var(--market-up)' : 'var(--market-down)', fontSize: 16, marginBottom: 20, fontWeight: 600 }}>
              {selectedQuote.change >= 0 ? '+' : ''}{selectedQuote.change.toFixed(2)} ({selectedQuote.change_pct >= 0 ? '+' : ''}{selectedQuote.change_pct.toFixed(2)}%)
            </div>

            {[
              ['开盘', selectedQuote.open.toFixed(2)],
              ['最高', selectedQuote.high.toFixed(2)],
              ['最低', selectedQuote.low.toFixed(2)],
              ['昨收', selectedQuote.prev_close.toFixed(2)],
              ['换手率', selectedQuote.turnover_rate ? selectedQuote.turnover_rate.toFixed(2) + '%' : '--'],
              ['市盈率', selectedQuote.pe_ratio ? selectedQuote.pe_ratio.toFixed(1) : '--'],
            ].map(([label, value]) => (
              <div key={label} style={{
                display: 'flex', justifyContent: 'space-between',
                padding: '10px 0', borderBottom: '1px solid var(--bg-border)', fontSize: 13,
              }}>
                <span style={{ color: 'var(--text-muted)' }}>{label}</span>
                <span style={{ fontWeight: 600 }}>{value}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
