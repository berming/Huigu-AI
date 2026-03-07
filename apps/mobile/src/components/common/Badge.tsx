import React from 'react';
import { Text, View, StyleSheet } from 'react-native';
import { Colors, Radius } from '../../constants/theme';

interface Props {
  label: string;
  color?: string;
  bgColor?: string;
}

export function Badge({ label, color = Colors.text.primary, bgColor = Colors.bg.elevated }: Props) {
  return (
    <View style={[styles.badge, { backgroundColor: bgColor }]}>
      <Text style={[styles.text, { color }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: Radius.sm,
  },
  text: {
    fontSize: 10,
    fontWeight: '600',
  },
});
