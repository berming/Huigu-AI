import React from 'react';
import { Text, View, StyleSheet } from 'react-native';
import { Colors, Typography } from '../../constants/theme';

interface Props {
  value: number;
  suffix?: string;
  size?: 'sm' | 'md' | 'lg';
  showSign?: boolean;
}

export function PriceChange({ value, suffix = '%', size = 'md', showSign = true }: Props) {
  const isUp = value > 0;
  const isFlat = value === 0;
  const color = isFlat ? Colors.market.flat : isUp ? Colors.market.up : Colors.market.down;
  const sign = showSign ? (isUp ? '+' : '') : '';

  const fontSize = size === 'lg' ? 18 : size === 'md' ? 14 : 12;

  return (
    <Text style={[styles.text, { color, fontSize, fontWeight: '600' }]}>
      {sign}{value.toFixed(2)}{suffix}
    </Text>
  );
}

const styles = StyleSheet.create({
  text: { fontVariant: ['tabular-nums'] },
});
