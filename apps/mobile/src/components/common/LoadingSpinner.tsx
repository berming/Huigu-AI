import React from 'react';
import { View, ActivityIndicator, Text, StyleSheet } from 'react-native';
import { Colors } from '../../constants/theme';

interface Props {
  text?: string;
}

export function LoadingSpinner({ text }: Props) {
  return (
    <View style={styles.container}>
      <ActivityIndicator size="large" color={Colors.brand.primary} />
      {text && <Text style={styles.text}>{text}</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: Colors.bg.primary,
    gap: 12,
  },
  text: {
    color: Colors.text.secondary,
    fontSize: 14,
  },
});
