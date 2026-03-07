import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Colors, Spacing, Radius } from '../../constants/theme';
import { StockQuote } from '../../services/api';
import { PriceChange } from '../common/PriceChange';

interface Props {
  quote: StockQuote;
  onPress?: () => void;
}

function formatAmount(v: number): string {
  if (v >= 1e8) return `${(v / 1e8).toFixed(2)}亿`;
  if (v >= 1e4) return `${(v / 1e4).toFixed(2)}万`;
  return v.toFixed(0);
}

export function StockCard({ quote, onPress }: Props) {
  const isUp = quote.change_pct > 0;
  const isDown = quote.change_pct < 0;
  const color = isUp ? Colors.market.up : isDown ? Colors.market.down : Colors.market.flat;
  const bgColor = isUp ? Colors.market.upLight : isDown ? Colors.market.downLight : 'transparent';

  return (
    <TouchableOpacity onPress={onPress} activeOpacity={0.7} style={styles.container}>
      <View style={styles.left}>
        <Text style={styles.name} numberOfLines={1}>{quote.name}</Text>
        <Text style={styles.symbol}>{quote.symbol}</Text>
      </View>

      <View style={styles.middle}>
        <Text style={styles.subLabel}>成交额</Text>
        <Text style={styles.subValue}>{formatAmount(quote.amount)}</Text>
      </View>

      <View style={[styles.right, { backgroundColor: bgColor }]}>
        <Text style={[styles.price, { color }]}>{quote.price.toFixed(2)}</Text>
        <PriceChange value={quote.change_pct} size="sm" />
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
    borderBottomWidth: 0.5,
    borderBottomColor: Colors.bg.border,
    backgroundColor: Colors.bg.secondary,
  },
  left: { flex: 1 },
  name: {
    color: Colors.text.primary,
    fontSize: 15,
    fontWeight: '600',
    marginBottom: 2,
  },
  symbol: {
    color: Colors.text.secondary,
    fontSize: 11,
  },
  middle: {
    flex: 1,
    alignItems: 'center',
  },
  subLabel: {
    color: Colors.text.muted,
    fontSize: 10,
    marginBottom: 2,
  },
  subValue: {
    color: Colors.text.secondary,
    fontSize: 12,
  },
  right: {
    width: 90,
    alignItems: 'flex-end',
    paddingVertical: 6,
    paddingHorizontal: 8,
    borderRadius: Radius.sm,
  },
  price: {
    fontSize: 16,
    fontWeight: '700',
    fontVariant: ['tabular-nums'],
    marginBottom: 2,
  },
});
