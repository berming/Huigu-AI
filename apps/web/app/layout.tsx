import type { Metadata } from 'next';
import './globals.css';
import { Sidebar } from '@/components/Sidebar';
import { Providers } from '@/components/Providers';

export const metadata: Metadata = {
  title: '慧股AI — 智能投研平台',
  description: '基于Claude AI的A股智能分析平台',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>
        <Providers>
          <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
            <Sidebar />
            <main style={{ flex: 1, overflow: 'auto', background: 'var(--bg-primary)' }}>
              {children}
            </main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
