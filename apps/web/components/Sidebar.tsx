'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

const NAV = [
  { href: '/', icon: '📊', label: '行情' },
  { href: '/sentiment', icon: '💬', label: '热议' },
  { href: '/research', icon: '🤖', label: 'AI投研' },
  { href: '/profile', icon: '👤', label: '我的' },
];

export function Sidebar() {
  const path = usePathname();
  return (
    <aside style={{
      width: 200, flexShrink: 0, background: 'var(--bg-secondary)',
      borderRight: '1px solid var(--bg-border)',
      display: 'flex', flexDirection: 'column', height: '100vh',
    }}>
      {/* Logo */}
      <div style={{ padding: '24px 20px 20px', borderBottom: '1px solid var(--bg-border)' }}>
        <div style={{ color: 'var(--brand-primary)', fontSize: 20, fontWeight: 800, letterSpacing: 0.5 }}>
          慧股AI
        </div>
        <div style={{ color: 'var(--text-muted)', fontSize: 11, marginTop: 2 }}>智能投研平台</div>
      </div>

      {/* Nav */}
      <nav style={{ flex: 1, padding: '12px 10px' }}>
        {NAV.map(item => {
          const active = item.href === '/' ? path === '/' : path.startsWith(item.href);
          return (
            <Link key={item.href} href={item.href} style={{
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '10px 12px', borderRadius: 8, marginBottom: 4,
              background: active ? 'rgba(240,180,41,0.12)' : 'transparent',
              color: active ? 'var(--brand-primary)' : 'var(--text-secondary)',
              fontWeight: active ? 600 : 400, fontSize: 14,
              transition: 'all 0.15s',
            }}>
              <span style={{ fontSize: 18 }}>{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div style={{ padding: '16px 20px', borderTop: '1px solid var(--bg-border)' }}>
        <div style={{ color: 'var(--text-muted)', fontSize: 10, lineHeight: 1.6 }}>
          AI内容仅供参考<br />不构成投资建议
        </div>
      </div>
    </aside>
  );
}
