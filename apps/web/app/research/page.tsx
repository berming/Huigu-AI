'use client';
import { useState, useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { aiApi } from '@/lib/api';
import { useWatchlistStore } from '@/lib/store';
import { BullBearDebateCard } from '@/components/ai/BullBearDebate';
import { LoadingSpinner } from '@/components/common/LoadingSpinner';

const HOT_CONCEPTS = [
  { name: '低空经济', heat: 95, desc: '航空管理局放开低空空域，eVTOL产业链快速崛起', icon: '🚁' },
  { name: 'AI算力', heat: 92, desc: 'DeepSeek引爆国产大模型需求，算力基础设施加速扩容', icon: '🖥️' },
  { name: '人形机器人', heat: 88, desc: '特斯拉Optimus量产节点临近，国内产业链配套成熟', icon: '🤖' },
  { name: '合成生物', heat: 75, desc: '政策扶持+技术突破，生物制造产业迎来战略机遇期', icon: '🧬' },
  { name: '核电重启', heat: 72, desc: '国家核电发展规划加速，新建核电项目审批提速', icon: '⚛️' },
];

function AIStreamPanel({ url }: { url: string }) {
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setText('');
    setLoading(true);

    (async () => {
      try {
        const res = await fetch(url, { signal: ctrl.signal });
        const reader = res.body!.getReader();
        const dec = new TextDecoder();
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          setText(prev => prev + dec.decode(value));
        }
      } catch (_) { /* aborted */ }
      setLoading(false);
    })();

    return () => ctrl.abort();
  }, [url]);

  return (
    <div style={{
      background: 'var(--bg-card)', borderRadius: 12, border: '1px solid var(--bg-border)', padding: 20,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
        <span style={{ fontSize: 16 }}>🤖</span>
        <span style={{ fontWeight: 700, fontSize: 14 }}>Claude AI 智能分析</span>
        {loading && (
          <span style={{
            fontSize: 10, color: 'var(--ai-purple)', background: 'rgba(168,85,247,0.15)',
            padding: '2px 8px', borderRadius: 999, fontWeight: 600,
          }}>● 生成中</span>
        )}
      </div>
      {text ? (
        <p style={{ color: 'var(--text-secondary)', fontSize: 13, lineHeight: 1.8, whiteSpace: 'pre-wrap' }}>
          {text}
          {loading && <span style={{ color: 'var(--ai-purple)', animation: 'blink 1s step-start infinite' }}>▋</span>}
        </p>
      ) : loading ? (
        <LoadingSpinner text="AI分析中..." />
      ) : null}
      <style>{`@keyframes blink { 50% { opacity: 0; } }`}</style>
    </div>
  );
}

export default function ResearchPage() {
  const { stocks, names } = useWatchlistStore();
  const [selectedSymbol, setSelectedSymbol] = useState(stocks[0]?.symbol ?? '600519');
  const selectedName = names[selectedSymbol] ?? selectedSymbol;
  const [showDebate, setShowDebate] = useState(false);

  const { data: debate, isFetching: debateFetching, refetch: fetchDebate } = useQuery({
    queryKey: ['debate', selectedSymbol],
    queryFn: () => aiApi.debate(selectedSymbol, selectedName),
    enabled: false,
  });

  const handleDebate = async () => {
    setShowDebate(true);
    await fetchDebate();
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{
        padding: '16px 24px', background: 'var(--bg-secondary)',
        borderBottom: '1px solid var(--bg-border)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 800, marginBottom: 2 }}>AI投研</h1>
          <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>Claude AI 驱动的智能研究</div>
        </div>
        <span style={{
          fontSize: 12, color: 'var(--ai-purple)', background: 'rgba(168,85,247,0.15)',
          padding: '4px 12px', borderRadius: 999, fontWeight: 600, border: '1px solid rgba(168,85,247,0.4)',
        }}>⚡ Claude驱动</span>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: 24 }}>
        {/* Stock selector */}
        <div style={{ marginBottom: 24 }}>
          <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 10 }}>选择研究标的</div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {stocks.map(s => (
              <button key={s.symbol} onClick={() => { setSelectedSymbol(s.symbol); setShowDebate(false); }} style={{
                padding: '6px 16px', borderRadius: 999, fontSize: 13,
                background: s.symbol === selectedSymbol ? 'var(--brand-primary)' : 'var(--bg-elevated)',
                color: s.symbol === selectedSymbol ? 'var(--bg-primary)' : 'var(--text-secondary)',
                fontWeight: s.symbol === selectedSymbol ? 700 : 400,
                border: '1px solid transparent',
              }}>
                {s.name}
              </button>
            ))}
          </div>
        </div>

        {/* 2-column layout */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 24 }}>
          {/* AI stream */}
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 10 }}>🤖 智能分析</div>
            <AIStreamPanel key={selectedSymbol} url={aiApi.analyzeUrl(selectedSymbol, selectedName)} />
            <div style={{
              marginTop: 8, padding: '8px 12px', background: 'rgba(248,73,96,0.08)',
              border: '1px solid rgba(248,73,96,0.2)', borderRadius: 8,
              color: 'var(--text-muted)', fontSize: 11,
            }}>
              ⚠️ AI生成内容仅供参考，不构成投资建议，投资有风险，入市须谨慎
            </div>
          </div>

          {/* Bull/Bear debate */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
              <div style={{ fontSize: 14, fontWeight: 700 }}>⚔️ 多空辩论室</div>
              {!showDebate && (
                <button onClick={handleDebate} style={{
                  padding: '6px 16px', borderRadius: 999, fontSize: 13, fontWeight: 600,
                  background: 'var(--ai-purple)', color: '#fff',
                }}>生成辩论</button>
              )}
            </div>
            {showDebate && debateFetching && <LoadingSpinner text="AI生成中..." />}
            {showDebate && debate && <BullBearDebateCard debate={debate} />}
            {!showDebate && (
              <div style={{
                background: 'var(--bg-card)', borderRadius: 12, border: '1px solid var(--bg-border)',
                padding: 40, textAlign: 'center', color: 'var(--text-muted)',
              }}>
                <div style={{ fontSize: 32, marginBottom: 12 }}>⚔️</div>
                <div>点击「生成辩论」，让 AI 呈现多空两方的投资逻辑</div>
              </div>
            )}
          </div>
        </div>

        {/* Hot concepts */}
        <div>
          <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>🔥 热点概念追踪</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
            {HOT_CONCEPTS.map(c => (
              <div key={c.name} style={{
                background: 'var(--bg-card)', borderRadius: 10, border: '1px solid var(--bg-border)',
                padding: 16, display: 'flex', gap: 14, alignItems: 'flex-start',
              }}>
                <span style={{ fontSize: 28, flexShrink: 0 }}>{c.icon}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>{c.name}</div>
                  <div style={{ color: 'var(--text-muted)', fontSize: 12, lineHeight: 1.5, marginBottom: 8 }}>{c.desc}</div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{ flex: 1, height: 4, background: 'var(--bg-elevated)', borderRadius: 2, overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${c.heat}%`, background: 'var(--brand-primary)', borderRadius: 2 }} />
                    </div>
                    <span style={{ color: 'var(--brand-primary)', fontSize: 12, fontWeight: 700 }}>{c.heat}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
