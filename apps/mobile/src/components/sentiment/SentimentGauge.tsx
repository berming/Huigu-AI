import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Colors, Spacing, Radius } from '../../constants/theme';
import { SentimentScore } from '../../services/api';

interface Props {
  score: SentimentScore;
}

export function SentimentGauge({ score }: Props) {
  const bullPct = Math.round(score.bull_ratio * 100);
  const bearPct = Math.round(score.bear_ratio * 100);
  const neutralPct = Math.round(score.neutral_ratio * 100);

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>市场情绪</Text>
        <View style={styles.heatBadge}>
          <Text style={styles.heatLabel}>热度 </Text>
          <Text style={styles.heatValue}>{score.heat_score.toFixed(0)}</Text>
        </View>
      </View>

      {/* Bar */}
      <View style={styles.bar}>
        <View style={[styles.segment, { flex: score.bull_ratio, backgroundColor: Colors.sentiment.bull }]} />
        <View style={[styles.segment, { flex: score.neutral_ratio, backgroundColor: Colors.sentiment.neutral }]} />
        <View style={[styles.segment, { flex: score.bear_ratio, backgroundColor: Colors.sentiment.bear }]} />
      </View>

      {/* Labels */}
      <View style={styles.labels}>
        <View style={styles.labelItem}>
          <View style={[styles.dot, { backgroundColor: Colors.sentiment.bull }]} />
          <Text style={styles.labelText}>看多 {bullPct}%</Text>
        </View>
        <View style={styles.labelItem}>
          <View style={[styles.dot, { backgroundColor: Colors.sentiment.neutral }]} />
          <Text style={styles.labelText}>中性 {neutralPct}%</Text>
        </View>
        <View style={styles.labelItem}>
          <View style={[styles.dot, { backgroundColor: Colors.sentiment.bear }]} />
          <Text style={styles.labelText}>看空 {bearPct}%</Text>
        </View>
      </View>

      <Text style={styles.total}>共 {score.total_posts} 条讨论</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: Colors.bg.card,
    borderRadius: Radius.lg,
    padding: Spacing.lg,
    marginHorizontal: Spacing.lg,
    marginVertical: Spacing.sm,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: Spacing.md,
  },
  title: { color: Colors.text.primary, fontSize: 15, fontWeight: '600' },
  heatBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(240,180,41,0.15)',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: Radius.full,
  },
  heatLabel: { color: Colors.brand.primary, fontSize: 11 },
  heatValue: { color: Colors.brand.primary, fontSize: 14, fontWeight: '700' },
  bar: {
    flexDirection: 'row',
    height: 10,
    borderRadius: Radius.full,
    overflow: 'hidden',
    gap: 2,
    marginBottom: Spacing.md,
  },
  segment: { borderRadius: Radius.full },
  labels: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginBottom: Spacing.sm,
  },
  labelItem: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  dot: { width: 8, height: 8, borderRadius: 4 },
  labelText: { color: Colors.text.secondary, fontSize: 12 },
  total: { color: Colors.text.muted, fontSize: 11, textAlign: 'center' },
});
