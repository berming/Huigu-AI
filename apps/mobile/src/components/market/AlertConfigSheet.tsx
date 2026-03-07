/**
 * Price alert configuration bottom sheet.
 * Lets users set upper / lower price targets for a watched stock.
 */
import React, { useState, useEffect } from 'react';
import {
  View, Text, StyleSheet, Modal, TouchableOpacity,
  TextInput, Switch, Alert, KeyboardAvoidingView, Platform, ScrollView,
} from 'react-native';
import { Colors, Spacing, Radius } from '../../constants/theme';
import { useWatchlistStore, PriceAlert } from '../../store/watchlist';
import { StockQuote } from '../../services/api';

interface Props {
  visible: boolean;
  symbol: string;
  name: string;
  quote?: StockQuote;
  onClose: () => void;
}

export function AlertConfigSheet({ visible, symbol, name, quote, onClose }: Props) {
  const { getStock, setAlert, resetAlertTriggers } = useWatchlistStore();
  const stock = getStock(symbol);
  const alert = stock?.alert;

  const [enabled, setEnabled] = useState(alert?.enabled ?? false);
  const [upper, setUpper] = useState(alert?.upperTarget?.toString() ?? '');
  const [lower, setLower] = useState(alert?.lowerTarget?.toString() ?? '');

  // Sync when alert changes externally
  useEffect(() => {
    setEnabled(alert?.enabled ?? false);
    setUpper(alert?.upperTarget?.toString() ?? '');
    setLower(alert?.lowerTarget?.toString() ?? '');
  }, [visible]);

  const currentPrice = quote?.price;

  const validate = (): boolean => {
    const u = parseFloat(upper);
    const l = parseFloat(lower);
    if (upper && isNaN(u)) { Alert.alert('错误', '目标涨价格式不正确'); return false; }
    if (lower && isNaN(l)) { Alert.alert('错误', '预警跌价格式不正确'); return false; }
    if (upper && lower && u <= l) { Alert.alert('错误', '目标涨价必须高于预警跌价'); return false; }
    if (currentPrice) {
      if (upper && u <= currentPrice) {
        Alert.alert('提示', `目标涨价 ${u} 低于或等于当前价 ${currentPrice}，已保存但不会触发`);
      }
      if (lower && l >= currentPrice) {
        Alert.alert('提示', `预警跌价 ${l} 高于或等于当前价 ${currentPrice}，已保存但不会触发`);
      }
    }
    return true;
  };

  const handleSave = () => {
    if (!validate()) return;
    const partial: Partial<PriceAlert> = {
      enabled,
      upperTarget: upper ? parseFloat(upper) : undefined,
      lowerTarget: lower ? parseFloat(lower) : undefined,
    };
    setAlert(symbol, partial);
    resetAlertTriggers(symbol);
    onClose();
  };

  const handleClear = () => {
    setAlert(symbol, { enabled: false, upperTarget: undefined, lowerTarget: undefined });
    resetAlertTriggers(symbol);
    setEnabled(false);
    setUpper('');
    setLower('');
    onClose();
  };

  const fillCurrentUpper = () => currentPrice && setUpper((currentPrice * 1.05).toFixed(2));
  const fillCurrentLower = () => currentPrice && setLower((currentPrice * 0.95).toFixed(2));

  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={onClose}
    >
      <TouchableOpacity style={styles.backdrop} activeOpacity={1} onPress={onClose} />
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={styles.sheet}
      >
        {/* Handle */}
        <View style={styles.handle} />

        <Text style={styles.title}>价格提醒设置</Text>
        <Text style={styles.subtitle}>{name} · {symbol}</Text>

        {currentPrice !== undefined && (
          <View style={styles.currentPriceRow}>
            <Text style={styles.currentPriceLabel}>当前价格</Text>
            <Text style={styles.currentPriceValue}>{currentPrice.toFixed(2)}</Text>
          </View>
        )}

        {/* Enable toggle */}
        <View style={styles.toggleRow}>
          <View>
            <Text style={styles.toggleLabel}>启用价格提醒</Text>
            <Text style={styles.toggleSub}>触发后 App 内弹出提示</Text>
          </View>
          <Switch
            value={enabled}
            onValueChange={setEnabled}
            trackColor={{ true: Colors.brand.primary, false: Colors.bg.border }}
            thumbColor="#fff"
          />
        </View>

        <ScrollView showsVerticalScrollIndicator={false}>
          {/* Upper target */}
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <View style={[styles.sectionDot, { backgroundColor: Colors.market.up }]} />
              <Text style={styles.sectionTitle}>目标涨价（触达提醒买卖）</Text>
            </View>
            <View style={styles.inputRow}>
              <TextInput
                style={styles.input}
                value={upper}
                onChangeText={setUpper}
                placeholder="输入目标价格"
                placeholderTextColor={Colors.text.muted}
                keyboardType="decimal-pad"
                editable={enabled}
              />
              {currentPrice && (
                <TouchableOpacity style={styles.quickBtn} onPress={fillCurrentUpper} disabled={!enabled}>
                  <Text style={styles.quickBtnText}>+5%</Text>
                </TouchableOpacity>
              )}
            </View>
            {upper && currentPrice && (
              <Text style={styles.hint}>
                较当前价 {(((parseFloat(upper) - currentPrice) / currentPrice) * 100).toFixed(1)}%
              </Text>
            )}
          </View>

          {/* Lower target */}
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <View style={[styles.sectionDot, { backgroundColor: Colors.market.down }]} />
              <Text style={styles.sectionTitle}>预警跌价（触达提醒止损）</Text>
            </View>
            <View style={styles.inputRow}>
              <TextInput
                style={styles.input}
                value={lower}
                onChangeText={setLower}
                placeholder="输入预警价格"
                placeholderTextColor={Colors.text.muted}
                keyboardType="decimal-pad"
                editable={enabled}
              />
              {currentPrice && (
                <TouchableOpacity style={styles.quickBtn} onPress={fillCurrentLower} disabled={!enabled}>
                  <Text style={styles.quickBtnText}>-5%</Text>
                </TouchableOpacity>
              )}
            </View>
            {lower && currentPrice && (
              <Text style={[styles.hint, { color: Colors.market.down }]}>
                较当前价 {(((parseFloat(lower) - currentPrice) / currentPrice) * 100).toFixed(1)}%
              </Text>
            )}
          </View>
        </ScrollView>

        {/* Actions */}
        <View style={styles.actions}>
          <TouchableOpacity style={styles.clearBtn} onPress={handleClear}>
            <Text style={styles.clearBtnText}>清除提醒</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.saveBtn} onPress={handleSave}>
            <Text style={styles.saveBtnText}>保存</Text>
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
  },
  sheet: {
    backgroundColor: Colors.bg.secondary,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    paddingHorizontal: Spacing.lg,
    paddingBottom: 36,
    maxHeight: '85%',
  },
  handle: {
    width: 36, height: 4,
    backgroundColor: Colors.bg.border,
    borderRadius: 2,
    alignSelf: 'center',
    marginTop: 10,
    marginBottom: Spacing.md,
  },
  title: { color: Colors.text.primary, fontSize: 18, fontWeight: '700', textAlign: 'center' },
  subtitle: { color: Colors.text.secondary, fontSize: 13, textAlign: 'center', marginTop: 4, marginBottom: Spacing.lg },
  currentPriceRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: Colors.bg.elevated,
    padding: Spacing.md,
    borderRadius: Radius.md,
    marginBottom: Spacing.lg,
  },
  currentPriceLabel: { color: Colors.text.secondary, fontSize: 13 },
  currentPriceValue: { color: Colors.text.primary, fontSize: 18, fontWeight: '700', fontVariant: ['tabular-nums'] },
  toggleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: Spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: Colors.bg.border,
    marginBottom: Spacing.lg,
  },
  toggleLabel: { color: Colors.text.primary, fontSize: 15, fontWeight: '600' },
  toggleSub: { color: Colors.text.muted, fontSize: 11, marginTop: 2 },
  section: { marginBottom: Spacing.lg },
  sectionHeader: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: Spacing.sm },
  sectionDot: { width: 8, height: 8, borderRadius: 4 },
  sectionTitle: { color: Colors.text.secondary, fontSize: 13, fontWeight: '600' },
  inputRow: { flexDirection: 'row', gap: Spacing.sm },
  input: {
    flex: 1,
    backgroundColor: Colors.bg.elevated,
    color: Colors.text.primary,
    fontSize: 16,
    paddingHorizontal: Spacing.md,
    paddingVertical: 12,
    borderRadius: Radius.md,
    fontVariant: ['tabular-nums'],
  },
  quickBtn: {
    backgroundColor: Colors.bg.elevated,
    paddingHorizontal: Spacing.md,
    borderRadius: Radius.md,
    justifyContent: 'center',
  },
  quickBtnText: { color: Colors.brand.primary, fontSize: 13, fontWeight: '600' },
  hint: { color: Colors.market.up, fontSize: 11, marginTop: 4, marginLeft: 4 },
  actions: { flexDirection: 'row', gap: Spacing.md, marginTop: Spacing.lg },
  clearBtn: {
    flex: 1, paddingVertical: 13,
    backgroundColor: Colors.bg.elevated,
    borderRadius: Radius.md, alignItems: 'center',
  },
  clearBtnText: { color: Colors.text.secondary, fontSize: 15 },
  saveBtn: {
    flex: 2, paddingVertical: 13,
    backgroundColor: Colors.brand.primary,
    borderRadius: Radius.md, alignItems: 'center',
  },
  saveBtnText: { color: Colors.bg.primary, fontSize: 15, fontWeight: '700' },
});
