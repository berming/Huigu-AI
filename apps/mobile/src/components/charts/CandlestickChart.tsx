import React, { useMemo, useState } from 'react';
import { View, Text, StyleSheet, Dimensions, TouchableOpacity, ScrollView } from 'react-native';
import { KLineBar } from '../../services/api';
import { Colors, Spacing, Radius } from '../../constants/theme';

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const CHART_HEIGHT = 220;
const VOLUME_HEIGHT = 60;
const BAR_WIDTH = 7;
const BAR_GAP = 2;
const VISIBLE_BARS = Math.floor((SCREEN_WIDTH - 40) / (BAR_WIDTH + BAR_GAP));

const PERIODS = ['日K', '周K', '月K'] as const;
type Period = typeof PERIODS[number];

interface Props {
  bars: KLineBar[];
  period: Period;
  onPeriodChange: (p: Period) => void;
}

export function CandlestickChart({ bars, period, onPeriodChange }: Props) {
  const displayBars = bars.slice(-VISIBLE_BARS);

  const { minPrice, maxPrice, maxVolume } = useMemo(() => {
    if (!displayBars.length) return { minPrice: 0, maxPrice: 1, maxVolume: 1 };
    const prices = displayBars.flatMap(b => [b.high, b.low]);
    return {
      minPrice: Math.min(...prices),
      maxPrice: Math.max(...prices),
      maxVolume: Math.max(...displayBars.map(b => b.volume)),
    };
  }, [displayBars]);

  const priceRange = maxPrice - minPrice || 1;

  const toY = (price: number) =>
    ((maxPrice - price) / priceRange) * CHART_HEIGHT;

  if (!displayBars.length) {
    return (
      <View style={styles.empty}>
        <Text style={styles.emptyText}>暂无K线数据</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Period selector */}
      <View style={styles.periodRow}>
        {PERIODS.map(p => (
          <TouchableOpacity
            key={p}
            onPress={() => onPeriodChange(p)}
            style={[styles.periodBtn, period === p && styles.periodBtnActive]}
          >
            <Text style={[styles.periodText, period === p && styles.periodTextActive]}>{p}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Price labels */}
      <View style={styles.priceAxis}>
        <Text style={styles.axisLabel}>{maxPrice.toFixed(2)}</Text>
        <Text style={styles.axisLabel}>{((maxPrice + minPrice) / 2).toFixed(2)}</Text>
        <Text style={styles.axisLabel}>{minPrice.toFixed(2)}</Text>
      </View>

      {/* Candlestick SVG-like with Views */}
      <View style={styles.chartArea}>
        {displayBars.map((bar, i) => {
          const isUp = bar.close >= bar.open;
          const color = isUp ? Colors.market.up : Colors.market.down;

          const bodyTop = toY(Math.max(bar.open, bar.close));
          const bodyHeight = Math.max(1, Math.abs(toY(bar.open) - toY(bar.close)));
          const wickTop = toY(bar.high);
          const wickHeight = toY(bar.low) - wickTop;

          const volHeight = maxVolume > 0 ? (bar.volume / maxVolume) * VOLUME_HEIGHT : 0;

          return (
            <View
              key={bar.date + i}
              style={[styles.barContainer, { width: BAR_WIDTH }]}
            >
              {/* Wick */}
              <View style={[styles.wick, { top: wickTop, height: wickHeight, backgroundColor: color }]} />
              {/* Body */}
              <View style={[styles.body, { top: bodyTop, height: bodyHeight, backgroundColor: color }]} />
              {/* Volume at bottom */}
              <View style={[styles.volume, { height: volHeight, backgroundColor: color, opacity: 0.6 }]} />
            </View>
          );
        })}
      </View>

      {/* Date labels */}
      <View style={styles.dateRow}>
        {[0, Math.floor(displayBars.length / 2), displayBars.length - 1].map(idx => (
          <Text key={idx} style={styles.dateLabel}>
            {displayBars[idx]?.date?.slice(5) ?? ''}
          </Text>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: Colors.bg.secondary,
    paddingVertical: Spacing.md,
  },
  empty: {
    height: CHART_HEIGHT,
    justifyContent: 'center',
    alignItems: 'center',
  },
  emptyText: { color: Colors.text.muted, fontSize: 14 },
  periodRow: {
    flexDirection: 'row',
    paddingHorizontal: Spacing.lg,
    gap: Spacing.sm,
    marginBottom: Spacing.sm,
  },
  periodBtn: {
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: Radius.sm,
    backgroundColor: Colors.bg.elevated,
  },
  periodBtnActive: {
    backgroundColor: Colors.brand.primary,
  },
  periodText: { color: Colors.text.secondary, fontSize: 12 },
  periodTextActive: { color: Colors.text.inverse, fontWeight: '700' },
  priceAxis: {
    position: 'absolute',
    right: Spacing.sm,
    top: 45,
    height: CHART_HEIGHT,
    justifyContent: 'space-between',
    zIndex: 10,
  },
  axisLabel: { color: Colors.text.muted, fontSize: 9, fontVariant: ['tabular-nums'] },
  chartArea: {
    flexDirection: 'row',
    height: CHART_HEIGHT + VOLUME_HEIGHT,
    marginHorizontal: Spacing.lg,
    gap: BAR_GAP,
    position: 'relative',
  },
  barContainer: {
    height: CHART_HEIGHT + VOLUME_HEIGHT,
    position: 'relative',
  },
  wick: {
    position: 'absolute',
    width: 1,
    left: BAR_WIDTH / 2 - 0.5,
  },
  body: {
    position: 'absolute',
    width: BAR_WIDTH,
    left: 0,
  },
  volume: {
    position: 'absolute',
    width: BAR_WIDTH,
    bottom: 0,
    left: 0,
  },
  dateRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: Spacing.lg,
    marginTop: Spacing.xs,
  },
  dateLabel: { color: Colors.text.muted, fontSize: 9 },
});
