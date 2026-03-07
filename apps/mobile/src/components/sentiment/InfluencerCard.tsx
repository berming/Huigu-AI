import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Colors, Spacing, Radius } from '../../constants/theme';
import { Influencer } from '../../services/api';
import { Badge } from '../common/Badge';

const PLATFORM_ICONS: Record<string, string> = {
  weibo: '微博', xiaohongshu: '小红书', zhihu: '知乎', xueqiu: '雪球', guba: '股吧',
};

interface Props {
  influencer: Influencer;
  rank: number;
}

export function InfluencerCard({ influencer, rank }: Props) {
  const isBull = influencer.latest_view_sentiment === 'bullish';
  const winColor = influencer.win_rate >= 0.65 ? Colors.market.up : influencer.win_rate >= 0.55 ? Colors.brand.primary : Colors.market.down;

  return (
    <View style={styles.container}>
      <View style={styles.rankBadge}>
        <Text style={styles.rankText}>{rank}</Text>
      </View>

      <View style={styles.avatar}>
        <Text style={styles.avatarText}>{influencer.name[0]}</Text>
      </View>

      <View style={styles.info}>
        <View style={styles.nameRow}>
          <Text style={styles.name}>{influencer.name}</Text>
          <Text style={styles.platform}>{PLATFORM_ICONS[influencer.platform] ?? influencer.platform}</Text>
        </View>
        <Text style={styles.view} numberOfLines={2}>{influencer.latest_view}</Text>
      </View>

      <View style={styles.stats}>
        <Text style={[styles.winRate, { color: winColor }]}>{Math.round(influencer.win_rate * 100)}%</Text>
        <Text style={styles.statLabel}>胜率</Text>
        <Text style={styles.avgReturn}>+{influencer.avg_return}%</Text>
        <Text style={styles.statLabel}>平均收益</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.bg.card,
    borderRadius: Radius.md,
    padding: Spacing.md,
    marginHorizontal: Spacing.lg,
    marginVertical: Spacing.xs,
    gap: Spacing.sm,
  },
  rankBadge: {
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: Colors.bg.elevated,
    justifyContent: 'center',
    alignItems: 'center',
  },
  rankText: { color: Colors.text.secondary, fontSize: 11, fontWeight: '700' },
  avatar: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: Colors.bg.elevated,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1.5,
    borderColor: Colors.brand.primary,
  },
  avatarText: { color: Colors.brand.primary, fontSize: 16, fontWeight: '700' },
  info: { flex: 1 },
  nameRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 3 },
  name: { color: Colors.text.primary, fontSize: 14, fontWeight: '600' },
  platform: { color: Colors.text.muted, fontSize: 11 },
  view: { color: Colors.text.secondary, fontSize: 12, lineHeight: 17 },
  stats: { alignItems: 'flex-end' },
  winRate: { fontSize: 16, fontWeight: '700', fontVariant: ['tabular-nums'] },
  avgReturn: { color: Colors.market.up, fontSize: 12, fontWeight: '600' },
  statLabel: { color: Colors.text.muted, fontSize: 9, marginBottom: 4 },
});
