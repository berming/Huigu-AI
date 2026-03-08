/**
 * Watchlist stock card.
 * Shows: name / symbol / sparkline / price / change% / alert indicator.
 * Price cell flashes red / green on each tick update.
 */
import React, { useEffect, useRef } from 'react';
import { Text, View, StyleSheet, TouchableOpacity, Animated } from 'react-native';
import { Colors, Spacing, Radius } from '../../constants/theme';
import { StockQuote } from '../../services/api';
import { PriceChange } from '../common/PriceChange';
import { MiniSparkline } from '../charts/MiniSparkline';
import { useMarketStore, PriceDirection } from '../../store/market';
import { useWatchlistStore } from '../../store/watchlist';

interface Props {
  quote: StockQuote;
  onPress?: () => void;
  onAlertPress?: () => void;
}

function formatAmount(v: number): string {
  if (v >= 1e8) return `${(v / 1e8).toFixed(2)}亿`;
  if (v >= 1e4) return `${(v / 1e4).toFixed(2)}万`;
  return v.toFixed(0);
}

export function StockCard({ quote, onPress, onAlertPress }: Props) {
  const { sparklines, flashDir } = useMarketStore();
  const { getStock } = useWatchlistStore();

  const sparkData = sparklines[quote.symbol] ?? [quote.prev_close, quote.price];
  const dir: PriceDirection = flashDir[quote.symbol] ?? 'flat';
  const stock = getStock(quote.symbol);
  const hasAlert = stock?.alert.enabled && (stock.alert.upperTarget || stock.alert.lowerTarget);
  const alertTriggered = hasAlert && (stock!.alert.upperTriggered || stock!.alert.lowerTriggered);

  const isUp = quote.change_pct > 0;
  const isDown = quote.change_pct < 0;
  const priceColor = isUp ? Colors.market.up : isDown ? Colors.market.down : Colors.market.flat;
  const bgColor = isUp ? Colors.market.upLight : isDown ? Colors.market.downLight : 'transparent';

  // Flash animation on price update
  const flashAnim = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    if (dir === 'flat') return;
    flashAnim.setValue(1);
    Animated.timing(flashAnim, {
      toValue: 0,
      duration: 800,
      useNativeDriver: false,
    }).start();
  }, [quote.price]);

  const flashColor = flashAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [
      'transparent',
      dir === 'up' ? Colors.market.upLight : Colors.market.downLight,
    ],
  });

  return (
    <TouchableOpacity onPress={onPress} activeOpacity={0.7}>
      <Animated.View style={[styles.container, { backgroundColor: flashColor }]}>
        {/* Left: name + symbol + group */}
        <View style={styles.left}>
          <View style={styles.nameRow}>
            <Text style={styles.name} numberOfLines={1}>{quote.name}</Text>
            {alertTriggered && (
              <View style={styles.alertDot} />
            )}
          </View>
          <Text style={styles.symbol}>{quote.symbol}</Text>
        </View>

        {/* Center: sparkline */}
        <MiniSparkline data={sparkData} width={56} height={26} />

        {/* Right: price + change */}
        <View style={[styles.right, { backgroundColor: bgColor }]}>
          <Text style={[styles.price, { color: priceColor }]}>
            {quote.price.toFixed(2)}
          </Text>
          <PriceChange value={quote.change_pct} size="sm" />
        </View>

        {/* Alert bell button */}
        <TouchableOpacity
          style={styles.alertBtn}
          onPress={onAlertPress}
          hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
        >
          <Text style={[styles.alertIcon, hasAlert && styles.alertIconActive]}>
            {alertTriggered ? '🔔' : hasAlert ? '🔕' : '🔔'}
          </Text>
        </TouchableOpacity>
      </Animated.View>
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
    gap: Spacing.sm,
  },
  left: { flex: 1 },
  nameRow: { flexDirection: 'row', alignItems: 'center', gap: 5, marginBottom: 2 },
  name: { color: Colors.text.primary, fontSize: 15, fontWeight: '600', flexShrink: 1 },
  alertDot: { width: 6, height: 6, borderRadius: 3, backgroundColor: Colors.brand.primary },
  symbol: { color: Colors.text.secondary, fontSize: 11 },
  right: {
    width: 88,
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
  alertBtn: { paddingLeft: Spacing.xs },
  alertIcon: { fontSize: 14, opacity: 0.3 },
  alertIconActive: { opacity: 1 },
});
