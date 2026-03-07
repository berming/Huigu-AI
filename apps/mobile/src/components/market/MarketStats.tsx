import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Colors, Spacing, Radius } from '../../constants/theme';
import { MarketOverview } from '../../services/api';

interface Props {
  overview: MarketOverview;
}

export function MarketStats({ overview }: Props) {
  const total = overview.up_count + overview.down_count + overview.flat_count;
  const upPct = total > 0 ? overview.up_count / total : 0;

  return (
    <View style={styles.container}>
      <View style={styles.stat}>
        <Text style={[styles.count, { color: Colors.market.up }]}>{overview.up_count}</Text>
        <Text style={styles.label}>上涨</Text>
      </View>
      <View style={styles.progressBar}>
        <View style={[styles.progressUp, { flex: upPct }]} />
        <View style={[styles.progressDown, { flex: 1 - upPct }]} />
      </View>
      <View style={styles.stat}>
        <Text style={[styles.count, { color: Colors.market.down }]}>{overview.down_count}</Text>
        <Text style={styles.label}>下跌</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
    backgroundColor: Colors.bg.secondary,
    gap: Spacing.md,
  },
  stat: { alignItems: 'center', width: 48 },
  count: { fontSize: 16, fontWeight: '700', fontVariant: ['tabular-nums'] },
  label: { color: Colors.text.secondary, fontSize: 10, marginTop: 2 },
  progressBar: {
    flex: 1,
    height: 6,
    borderRadius: Radius.full,
    flexDirection: 'row',
    overflow: 'hidden',
    backgroundColor: Colors.bg.border,
  },
  progressUp: { backgroundColor: Colors.market.up },
  progressDown: { backgroundColor: Colors.market.down },
});
