import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Alert, ActivityIndicator } from 'react-native';
import { Colors, Spacing, Radius } from '../../constants/theme';
import { SocialPost } from '../../services/api';
import { aiApi } from '../../services/api';
import { Badge } from '../common/Badge';

const PLATFORM_ICONS: Record<string, string> = {
  weibo: '微博',
  xiaohongshu: '小红书',
  zhihu: '知乎',
  xueqiu: '雪球',
  guba: '股吧',
};

const SENTIMENT_LABELS: Record<string, { label: string; color: string; bg: string }> = {
  bullish: { label: '看多', color: Colors.market.up, bg: Colors.market.upLight },
  bearish: { label: '看空', color: Colors.market.down, bg: Colors.market.downLight },
  neutral: { label: '中性', color: Colors.text.secondary, bg: Colors.bg.elevated },
};

interface Props {
  post: SocialPost;
}

function timeAgo(iso: string): string {
  try {
    const diff = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 60) return `${mins}分钟前`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}小时前`;
    return `${Math.floor(hrs / 24)}天前`;
  } catch {
    return '';
  }
}

export function SocialPostCard({ post }: Props) {
  const [loadingSummary, setLoadingSummary] = useState(false);
  const sentiment = SENTIMENT_LABELS[post.sentiment] ?? SENTIMENT_LABELS.neutral;

  const handleLongPress = async () => {
    setLoadingSummary(true);
    try {
      const result = await aiApi.summarizePost(post.content);
      Alert.alert('AI核心逻辑', result.summary, [{ text: '关闭' }]);
    } catch {
      Alert.alert('提示', 'AI摘要暂不可用，请检查API配置');
    } finally {
      setLoadingSummary(false);
    }
  };

  return (
    <TouchableOpacity
      onLongPress={handleLongPress}
      activeOpacity={0.85}
      style={styles.container}
    >
      <View style={styles.header}>
        <View style={styles.authorRow}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>{post.author[0]}</Text>
          </View>
          <View>
            <View style={styles.authorNameRow}>
              <Text style={styles.author}>{post.author}</Text>
              {post.is_influencer && (
                <Badge label="达人" color={Colors.brand.primary} bgColor="rgba(240,180,41,0.15)" />
              )}
            </View>
            <Text style={styles.meta}>
              {PLATFORM_ICONS[post.platform] ?? post.platform} · {timeAgo(post.published_at)}
            </Text>
          </View>
        </View>
        <Badge label={sentiment.label} color={sentiment.color} bgColor={sentiment.bg} />
      </View>

      <Text style={styles.content} numberOfLines={3}>{post.content}</Text>

      <View style={styles.footer}>
        <Text style={styles.stats}>👍 {post.likes}  💬 {post.comments}</Text>
        {loadingSummary && <ActivityIndicator size="small" color={Colors.brand.primary} />}
        {!loadingSummary && <Text style={styles.hint}>长按获取AI摘要</Text>}
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: Colors.bg.card,
    borderRadius: Radius.md,
    padding: Spacing.md,
    marginHorizontal: Spacing.lg,
    marginVertical: Spacing.xs,
    borderWidth: 0.5,
    borderColor: Colors.bg.border,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: Spacing.sm,
  },
  authorRow: { flexDirection: 'row', gap: Spacing.sm, alignItems: 'center' },
  avatar: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: Colors.bg.elevated,
    justifyContent: 'center',
    alignItems: 'center',
  },
  avatarText: { color: Colors.brand.primary, fontSize: 14, fontWeight: '700' },
  authorNameRow: { flexDirection: 'row', alignItems: 'center', gap: 4, marginBottom: 2 },
  author: { color: Colors.text.primary, fontSize: 13, fontWeight: '600' },
  meta: { color: Colors.text.muted, fontSize: 11 },
  content: { color: Colors.text.secondary, fontSize: 13, lineHeight: 19, marginBottom: Spacing.sm },
  footer: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  stats: { color: Colors.text.muted, fontSize: 11 },
  hint: { color: Colors.text.muted, fontSize: 10, fontStyle: 'italic' },
});
