'use client';
import { SocialPost } from '@/lib/api';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/zh-cn';
dayjs.extend(relativeTime);
dayjs.locale('zh-cn');

const SENTIMENT_COLOR: Record<string, string> = {
  bullish: 'var(--market-up)', bearish: 'var(--market-down)', neutral: 'var(--market-flat)',
};
const SENTIMENT_LABEL: Record<string, string> = { bullish: '多', bearish: '空', neutral: '中' };

export function PostCard({ post }: { post: SocialPost }) {
  return (
    <div style={{
      background: 'var(--bg-card)', borderRadius: 10,
      border: '1px solid var(--bg-border)', padding: 14, marginBottom: 10,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{
            width: 32, height: 32, borderRadius: '50%',
            background: 'var(--bg-elevated)', display: 'flex', alignItems: 'center',
            justifyContent: 'center', fontSize: 14, fontWeight: 700,
            color: 'var(--brand-primary)',
          }}>
            {post.author.charAt(0)}
          </div>
          <div>
            <div style={{ fontSize: 13, fontWeight: 600 }}>
              {post.author}
              {post.is_influencer && (
                <span style={{ marginLeft: 6, fontSize: 10, color: 'var(--brand-primary)', background: 'rgba(240,180,41,0.15)', padding: '1px 6px', borderRadius: 4 }}>达人</span>
              )}
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{post.platform} · {dayjs(post.published_at).fromNow()}</div>
          </div>
        </div>
        <div style={{
          padding: '2px 10px', borderRadius: 999, fontSize: 12, fontWeight: 700,
          color: SENTIMENT_COLOR[post.sentiment],
          background: SENTIMENT_COLOR[post.sentiment] + '20',
        }}>
          {SENTIMENT_LABEL[post.sentiment]}
        </div>
      </div>
      <p style={{ color: 'var(--text-secondary)', fontSize: 13, lineHeight: 1.6, marginBottom: 10 }}>
        {post.content}
      </p>
      <div style={{ display: 'flex', gap: 16, color: 'var(--text-muted)', fontSize: 12 }}>
        <span>👍 {post.likes}</span>
        <span>💬 {post.comments}</span>
      </div>
    </div>
  );
}
