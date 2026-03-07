import React, { useState, useCallback } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity,
  StatusBar, Animated
} from 'react-native';
import { useQuery } from '@tanstack/react-query';
import { Colors, Spacing, Radius } from '../../constants/theme';
import { marketApi, sentimentApi, aiApi } from '../../services/api';
import { useWatchlistStore } from '../../store/watchlist';
import { CandlestickChart } from '../../components/charts/CandlestickChart';
import { SentimentGauge } from '../../components/sentiment/SentimentGauge';
import { SocialPostCard } from '../../components/sentiment/SocialPostCard';
import { InfluencerCard } from '../../components/sentiment/InfluencerCard';
import { AIStreamCard } from '../../components/ai/AIStreamCard';
import { BullBearDebateCard } from '../../components/ai/BullBearDebate';
import { DisclaimerBanner } from '../../components/common/DisclaimerBanner';
import { PriceChange } from '../../components/common/PriceChange';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';

type Tab = 'kline' | 'pankou' | 'hotdiscuss' | 'ai';
type Period = '日K' | '周K' | '月K';

const periodMap: Record<Period, string> = { '日K': 'D', '周K': 'W', '月K': 'M' };

interface Props {
  route: { params: { symbol: string; name: string } };
  navigation: any;
}

// Simulated order book data
function generateOrderBook(basePrice: number) {
  const asks = Array.from({ length: 5 }, (_, i) => ({
    price: basePrice + (5 - i) * 0.01 * basePrice * 0.002,
    volume: Math.floor(Math.random() * 5000) + 500,
  })).reverse();
  const bids = Array.from({ length: 5 }, (_, i) => ({
    price: basePrice - (i + 1) * 0.01 * basePrice * 0.002,
    volume: Math.floor(Math.random() * 5000) + 500,
  }));
  return { asks, bids };
}

export function StockDetailScreen({ route, navigation }: Props) {
  const { symbol, name } = route.params;
  const [activeTab, setActiveTab] = useState<Tab>('kline');
  const [period, setPeriod] = useState<Period>('日K');
  const [showDebate, setShowDebate] = useState(false);
  const { isWatched, addStock, removeStock } = useWatchlistStore();

  const watched = isWatched(symbol);

  const { data: quote } = useQuery({
    queryKey: ['quote', symbol],
    queryFn: () => marketApi.quote(symbol),
    refetchInterval: 10000,
  });

  const { data: kline, isLoading: klineLoading } = useQuery({
    queryKey: ['kline', symbol, period],
    queryFn: () => marketApi.kline(symbol, periodMap[period]),
    enabled: activeTab === 'kline',
  });

  const { data: sentiment } = useQuery({
    queryKey: ['sentiment', symbol],
    queryFn: () => sentimentApi.score(symbol, name),
    enabled: activeTab === 'hotdiscuss',
  });

  const { data: posts } = useQuery({
    queryKey: ['posts', symbol],
    queryFn: () => sentimentApi.posts(symbol, name, 20),
    enabled: activeTab === 'hotdiscuss',
  });

  const { data: influencers } = useQuery({
    queryKey: ['influencers', symbol],
    queryFn: () => sentimentApi.influencers(symbol, name),
    enabled: activeTab === 'hotdiscuss',
  });

  const { data: debate, isFetching: debateFetching, refetch: fetchDebate } = useQuery({
    queryKey: ['debate', symbol],
    queryFn: () => aiApi.debate(symbol, name),
    enabled: false,
  });

  const handleDebate = () => {
    setShowDebate(true);
    fetchDebate();
  };

  const price = quote?.price ?? 0;
  const isUp = (quote?.change_pct ?? 0) > 0;
  const priceColor = isUp ? Colors.market.up : (quote?.change_pct ?? 0) < 0 ? Colors.market.down : Colors.market.flat;

  const { asks, bids } = generateOrderBook(price || 10);

  const TABS: { key: Tab; label: string }[] = [
    { key: 'kline', label: 'K线' },
    { key: 'pankou', label: '盘口' },
    { key: 'hotdiscuss', label: '热议' },
    { key: 'ai', label: 'AI分析' },
  ];

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" />

      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
          <Text style={styles.backIcon}>‹</Text>
        </TouchableOpacity>
        <View style={styles.headerCenter}>
          <Text style={styles.stockName}>{name}</Text>
          <Text style={styles.stockCode}>{symbol}</Text>
        </View>
        <TouchableOpacity
          onPress={() => watched ? removeStock(symbol) : addStock(symbol, name)}
          style={[styles.watchBtn, watched && styles.watchBtnActive]}
        >
          <Text style={[styles.watchBtnText, watched && styles.watchBtnTextActive]}>
            {watched ? '已自选' : '+ 自选'}
          </Text>
        </TouchableOpacity>
      </View>

      {/* Price row */}
      {quote && (
        <View style={styles.priceRow}>
          <Text style={[styles.price, { color: priceColor }]}>{price.toFixed(2)}</Text>
          <View style={styles.priceChanges}>
            <PriceChange value={quote.change} suffix="" size="lg" />
            <PriceChange value={quote.change_pct} size="lg" />
          </View>
          <View style={styles.priceStats}>
            <View style={styles.statItem}>
              <Text style={styles.statLabel}>今开</Text>
              <Text style={styles.statValue}>{quote.open.toFixed(2)}</Text>
            </View>
            <View style={styles.statItem}>
              <Text style={styles.statLabel}>最高</Text>
              <Text style={[styles.statValue, { color: Colors.market.up }]}>{quote.high.toFixed(2)}</Text>
            </View>
            <View style={styles.statItem}>
              <Text style={styles.statLabel}>最低</Text>
              <Text style={[styles.statValue, { color: Colors.market.down }]}>{quote.low.toFixed(2)}</Text>
            </View>
            <View style={styles.statItem}>
              <Text style={styles.statLabel}>换手</Text>
              <Text style={styles.statValue}>{quote.turnover_rate?.toFixed(2) ?? '--'}%</Text>
            </View>
          </View>
        </View>
      )}

      {/* Tabs */}
      <View style={styles.tabs}>
        {TABS.map(tab => (
          <TouchableOpacity
            key={tab.key}
            style={[styles.tab, activeTab === tab.key && styles.tabActive]}
            onPress={() => setActiveTab(tab.key)}
          >
            <Text style={[styles.tabText, activeTab === tab.key && styles.tabTextActive]}>
              {tab.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Tab content */}
      <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>

        {/* K线 */}
        {activeTab === 'kline' && (
          <>
            {klineLoading ? (
              <LoadingSpinner text="加载K线..." />
            ) : (
              <CandlestickChart
                bars={kline?.bars ?? []}
                period={period}
                onPeriodChange={setPeriod}
              />
            )}
            {/* Trade buttons */}
            <View style={styles.tradeRow}>
              <TouchableOpacity style={styles.buyBtn}>
                <Text style={styles.buyBtnText}>买入</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.sellBtn}>
                <Text style={styles.sellBtnText}>卖出</Text>
              </TouchableOpacity>
            </View>
          </>
        )}

        {/* 盘口 */}
        {activeTab === 'pankou' && (
          <View style={styles.pankouContainer}>
            {/* Asks (sell orders) */}
            {asks.map((ask, i) => (
              <View key={i} style={[styles.orderRow, styles.askRow]}>
                <Text style={styles.orderLabel}>卖{5 - i}</Text>
                <Text style={[styles.orderPrice, { color: Colors.market.down }]}>{ask.price.toFixed(2)}</Text>
                <Text style={styles.orderVol}>{ask.volume}</Text>
              </View>
            ))}

            {/* Current price divider */}
            <View style={styles.pankouCenter}>
              <Text style={[styles.pankouPrice, { color: priceColor }]}>{price.toFixed(2)}</Text>
              <PriceChange value={quote?.change_pct ?? 0} />
            </View>

            {/* Bids (buy orders) */}
            {bids.map((bid, i) => (
              <View key={i} style={[styles.orderRow, styles.bidRow]}>
                <Text style={styles.orderLabel}>买{i + 1}</Text>
                <Text style={[styles.orderPrice, { color: Colors.market.up }]}>{bid.price.toFixed(2)}</Text>
                <Text style={styles.orderVol}>{bid.volume}</Text>
              </View>
            ))}

            {/* Flash order buttons */}
            <View style={styles.tradeRow}>
              <TouchableOpacity style={styles.buyBtn} onPress={() => {}}>
                <Text style={styles.buyBtnText}>闪电买入</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.sellBtn} onPress={() => {}}>
                <Text style={styles.sellBtnText}>闪电卖出</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}

        {/* 热议 */}
        {activeTab === 'hotdiscuss' && (
          <>
            {sentiment && <SentimentGauge score={sentiment} />}

            {/* Influencers section */}
            {influencers && influencers.length > 0 && (
              <>
                <Text style={styles.subSectionTitle}>🏆 达人榜</Text>
                {influencers.slice(0, 3).map((inf, i) => (
                  <InfluencerCard key={inf.id} influencer={inf} rank={i + 1} />
                ))}
              </>
            )}

            <Text style={styles.subSectionTitle}>💬 最新讨论</Text>
            {posts?.map(post => (
              <SocialPostCard key={post.id} post={post} />
            ))}
          </>
        )}

        {/* AI分析 */}
        {activeTab === 'ai' && (
          <>
            {/* Streaming analysis */}
            <AIStreamCard
              url={aiApi.analyzeUrl(symbol, name)}
            />

            <DisclaimerBanner />

            {/* Bull/Bear debate */}
            <View style={styles.debateHeader}>
              <Text style={styles.subSectionTitle}>⚔️ 多空辩论室</Text>
              {!showDebate && (
                <TouchableOpacity style={styles.debateBtn} onPress={handleDebate}>
                  <Text style={styles.debateBtnText}>生成辩论</Text>
                </TouchableOpacity>
              )}
            </View>

            {showDebate && debateFetching && (
              <LoadingSpinner text="AI正在生成多空辩论..." />
            )}

            {showDebate && debate && !debateFetching && (
              <BullBearDebateCard debate={debate} />
            )}
          </>
        )}

        <View style={{ height: 80 }} />
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg.primary },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingTop: 50,
    paddingHorizontal: Spacing.md,
    paddingBottom: Spacing.md,
    backgroundColor: Colors.bg.secondary,
    gap: Spacing.sm,
  },
  backBtn: { padding: Spacing.xs },
  backIcon: { color: Colors.text.primary, fontSize: 28, lineHeight: 28 },
  headerCenter: { flex: 1 },
  stockName: { color: Colors.text.primary, fontSize: 17, fontWeight: '700' },
  stockCode: { color: Colors.text.secondary, fontSize: 11 },
  watchBtn: {
    paddingHorizontal: 12,
    paddingVertical: 5,
    borderRadius: Radius.full,
    borderWidth: 1,
    borderColor: Colors.brand.primary,
  },
  watchBtnActive: { backgroundColor: Colors.brand.primary },
  watchBtnText: { color: Colors.brand.primary, fontSize: 12, fontWeight: '600' },
  watchBtnTextActive: { color: Colors.text.inverse },
  priceRow: {
    backgroundColor: Colors.bg.secondary,
    paddingHorizontal: Spacing.lg,
    paddingBottom: Spacing.md,
    gap: Spacing.xs,
  },
  price: { fontSize: 32, fontWeight: '800', fontVariant: ['tabular-nums'] },
  priceChanges: { flexDirection: 'row', gap: Spacing.lg },
  priceStats: {
    flexDirection: 'row',
    marginTop: Spacing.xs,
    gap: Spacing.xl,
  },
  statItem: {},
  statLabel: { color: Colors.text.muted, fontSize: 10, marginBottom: 2 },
  statValue: { color: Colors.text.secondary, fontSize: 12, fontVariant: ['tabular-nums'] },
  tabs: {
    flexDirection: 'row',
    backgroundColor: Colors.bg.secondary,
    borderBottomWidth: 1,
    borderBottomColor: Colors.bg.border,
  },
  tab: { flex: 1, paddingVertical: 11, alignItems: 'center' },
  tabActive: { borderBottomWidth: 2, borderBottomColor: Colors.brand.primary },
  tabText: { color: Colors.text.secondary, fontSize: 13 },
  tabTextActive: { color: Colors.brand.primary, fontWeight: '700' },
  content: { flex: 1 },
  tradeRow: {
    flexDirection: 'row',
    margin: Spacing.lg,
    gap: Spacing.md,
  },
  buyBtn: {
    flex: 1, paddingVertical: 13, backgroundColor: Colors.market.up,
    borderRadius: Radius.md, alignItems: 'center',
  },
  sellBtn: {
    flex: 1, paddingVertical: 13, backgroundColor: Colors.market.down,
    borderRadius: Radius.md, alignItems: 'center',
  },
  buyBtnText: { color: '#fff', fontSize: 15, fontWeight: '700' },
  sellBtnText: { color: '#fff', fontSize: 15, fontWeight: '700' },
  pankouContainer: { padding: Spacing.lg },
  orderRow: { flexDirection: 'row', paddingVertical: 6, gap: Spacing.lg },
  askRow: { backgroundColor: 'rgba(248,73,96,0.04)' },
  bidRow: { backgroundColor: 'rgba(38,161,123,0.04)' },
  orderLabel: { width: 30, color: Colors.text.muted, fontSize: 12 },
  orderPrice: { width: 70, fontSize: 13, fontVariant: ['tabular-nums'], fontWeight: '600' },
  orderVol: { flex: 1, color: Colors.text.secondary, fontSize: 12, textAlign: 'right' },
  pankouCenter: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.lg,
    paddingVertical: 10,
    borderTopWidth: 0.5,
    borderBottomWidth: 0.5,
    borderColor: Colors.bg.border,
    marginVertical: 4,
  },
  pankouPrice: { fontSize: 20, fontWeight: '700', fontVariant: ['tabular-nums'] },
  subSectionTitle: {
    color: Colors.text.primary,
    fontSize: 15,
    fontWeight: '700',
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
  },
  debateHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingRight: Spacing.lg,
  },
  debateBtn: {
    backgroundColor: Colors.ai.purple,
    paddingHorizontal: 16,
    paddingVertical: 7,
    borderRadius: Radius.full,
  },
  debateBtnText: { color: '#fff', fontSize: 13, fontWeight: '600' },
});
