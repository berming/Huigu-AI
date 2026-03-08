'use client';
import { useWatchlistStore } from '@/lib/store';

const INVESTOR_TYPES = [
  { label: '长线价投', icon: '📈', desc: '关注基本面，持股周期长', active: true },
  { label: '短线打板', icon: '⚡', desc: '追涨停板，快进快出', active: false },
  { label: '技术派', icon: '📊', desc: '以技术指标为主要决策依据', active: false },
];

const MENU = [
  { icon: '🔔', label: '价格提醒', sub: '设置涨跌提醒' },
  { icon: '📋', label: '模拟交易', sub: '纸上交易练习' },
  { icon: '📰', label: '研报库', sub: '近期精选研报' },
  { icon: '⚙️', label: '设置', sub: '账户与偏好设置' },
  { icon: '❓', label: '帮助与反馈', sub: '联系我们' },
];

export default function ProfilePage() {
  const { stocks } = useWatchlistStore();

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: '32px 24px', overflowY: 'auto', height: '100%' }}>
      {/* Hero */}
      <div style={{ textAlign: 'center', marginBottom: 32 }}>
        <div style={{
          width: 80, height: 80, borderRadius: '50%', background: 'var(--brand-primary)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          margin: '0 auto 16px', fontSize: 32, fontWeight: 900, color: 'var(--bg-primary)',
          boxShadow: '0 0 30px rgba(240,180,41,0.3)',
        }}>慧</div>
        <div style={{ fontSize: 20, fontWeight: 700, marginBottom: 4 }}>慧股AI用户</div>
        <div style={{ color: 'var(--text-secondary)', fontSize: 13 }}>智慧投资，理性决策</div>
      </div>

      {/* Stats */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 1,
        background: 'var(--bg-border)', borderRadius: 12, overflow: 'hidden', marginBottom: 32,
      }}>
        {[
          { label: '自选股', value: stocks.length, color: 'var(--text-primary)' },
          { label: '模拟收益', value: '+12.3%', color: 'var(--market-up)' },
          { label: 'AI分析次数', value: 28, color: 'var(--text-primary)' },
        ].map(s => (
          <div key={s.label} style={{ background: 'var(--bg-card)', padding: '20px', textAlign: 'center' }}>
            <div style={{ fontSize: 26, fontWeight: 800, color: s.color, marginBottom: 4 }}>{s.value}</div>
            <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* Investor type */}
      <div style={{ marginBottom: 32 }}>
        <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 12 }}>投资风格</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
          {INVESTOR_TYPES.map(t => (
            <div key={t.label} style={{
              background: t.active ? 'rgba(240,180,41,0.08)' : 'var(--bg-card)',
              borderRadius: 10, padding: 16, textAlign: 'center',
              border: `1px solid ${t.active ? 'var(--brand-primary)' : 'var(--bg-border)'}`,
            }}>
              <div style={{ fontSize: 24, marginBottom: 8 }}>{t.icon}</div>
              <div style={{ fontWeight: 700, fontSize: 13, color: t.active ? 'var(--brand-primary)' : 'var(--text-primary)', marginBottom: 4 }}>{t.label}</div>
              <div style={{ color: 'var(--text-muted)', fontSize: 11 }}>{t.desc}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Menu */}
      <div style={{ background: 'var(--bg-card)', borderRadius: 12, border: '1px solid var(--bg-border)', marginBottom: 32 }}>
        {MENU.map((item, i) => (
          <button key={item.label} style={{
            display: 'flex', alignItems: 'center', width: '100%', padding: '14px 20px', gap: 14, textAlign: 'left',
            borderBottom: i < MENU.length - 1 ? '1px solid var(--bg-border)' : 'none',
            transition: 'background 0.15s',
          }}
            onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-elevated)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
          >
            <span style={{ fontSize: 20, width: 28 }}>{item.icon}</span>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 14, fontWeight: 500 }}>{item.label}</div>
              <div style={{ color: 'var(--text-muted)', fontSize: 11, marginTop: 2 }}>{item.sub}</div>
            </div>
            <span style={{ color: 'var(--text-muted)', fontSize: 20 }}>›</span>
          </button>
        ))}
      </div>

      {/* Disclaimer */}
      <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: 11, lineHeight: 1.8 }}>
        <div>慧股AI — 您的智能投研助手</div>
        <div>所有AI生成内容仅供参考，不构成投资建议</div>
        <div>投资有风险，入市须谨慎</div>
        <div style={{ marginTop: 8 }}>v1.0.0</div>
      </div>
    </div>
  );
}
