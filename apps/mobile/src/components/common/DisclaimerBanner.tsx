import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Colors, Spacing, Radius } from '../../constants/theme';

export function DisclaimerBanner() {
  return (
    <View style={styles.container}>
      <Text style={styles.text}>
        ⚠️ 以上内容由AI生成，仅供参考，不构成投资建议。投资有风险，入市须谨慎。
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: 'rgba(240,180,41,0.1)',
    borderWidth: 1,
    borderColor: 'rgba(240,180,41,0.3)',
    borderRadius: Radius.md,
    padding: Spacing.md,
    marginHorizontal: Spacing.lg,
    marginVertical: Spacing.sm,
  },
  text: {
    color: Colors.brand.primary,
    fontSize: 11,
    lineHeight: 16,
    textAlign: 'center',
  },
});
