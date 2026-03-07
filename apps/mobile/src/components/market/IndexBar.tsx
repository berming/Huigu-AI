import React from 'react';
import { ScrollView, View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Colors, Spacing, Radius } from '../../constants/theme';
import { IndexQuote } from '../../services/api';
import { PriceChange } from '../common/PriceChange';

interface Props {
  indices: IndexQuote[];
}

export function IndexBar({ indices }: Props) {
  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      style={styles.scroll}
      contentContainerStyle={styles.content}
    >
      {indices.map(idx => {
        const isUp = idx.change_pct >= 0;
        const color = idx.change_pct === 0 ? Colors.market.flat : isUp ? Colors.market.up : Colors.market.down;
        return (
          <View key={idx.symbol} style={styles.item}>
            <Text style={styles.name} numberOfLines={1}>{idx.name}</Text>
            <Text style={[styles.price, { color }]}>
              {idx.price.toFixed(2)}
            </Text>
            <PriceChange value={idx.change_pct} size="sm" />
          </View>
        );
      })}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: {
    backgroundColor: Colors.bg.secondary,
    borderBottomWidth: 1,
    borderBottomColor: Colors.bg.border,
  },
  content: {
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    gap: Spacing.lg,
  },
  item: {
    alignItems: 'center',
    minWidth: 80,
  },
  name: {
    color: Colors.text.secondary,
    fontSize: 11,
    marginBottom: 2,
  },
  price: {
    fontSize: 14,
    fontWeight: '700',
    fontVariant: ['tabular-nums'],
    marginBottom: 1,
  },
});
