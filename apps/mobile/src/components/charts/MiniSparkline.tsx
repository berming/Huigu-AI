/**
 * Tiny inline sparkline for watchlist rows.
 * Pure View-based — no SVG dependency required.
 */
import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Colors } from '../../constants/theme';

interface Props {
  data: number[];         // price series, last N points
  width?: number;
  height?: number;
  color?: string;
}

export function MiniSparkline({ data, width = 60, height = 28, color }: Props) {
  if (data.length < 2) return <View style={{ width, height }} />;

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;

  const barWidth = width / data.length;
  const isUp = data[data.length - 1] >= data[0];
  const lineColor = color ?? (isUp ? Colors.market.up : Colors.market.down);

  return (
    <View style={[styles.container, { width, height }]}>
      {data.map((price, i) => {
        const barH = Math.max(1, ((price - min) / range) * (height - 2));
        return (
          <View
            key={i}
            style={[
              styles.bar,
              {
                width: Math.max(1, barWidth - 0.5),
                height: barH,
                backgroundColor: lineColor,
                opacity: i === data.length - 1 ? 1 : 0.45,
              },
            ]}
          />
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    overflow: 'hidden',
  },
  bar: {
    borderRadius: 0.5,
  },
});
