import React, { useCallback, useEffect, useState, useRef } from 'react';
import {
  View, Text, StyleSheet, FlatList,
  TouchableOpacity, RefreshControl, StatusBar, Alert,
} from 'react-native';
import { useQuery } from '@tanstack/react-query';
import { Colors, Spacing, Radius } from '../../constants/theme';
import { marketApi } from '../../services/api';
import { useWatchlistStore } from '../../store/watchlist';
import { useMarketStore } from '../../store/market';
import { IndexBar } from '../../components/market/IndexBar';
import { MarketStats } from '../../components/market/MarketStats';
import { StockCard } from '../../components/market/StockCard';
import { AlertConfigSheet } from '../../components/market/AlertConfigSheet';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';

interface Props {
  navigation: any;
}

export function MarketScreen({ navigation }: Props) {
  const { stocks, symbols, hydrated } = useWatchlistStore();
  const { setQuotes, setOverview, quotes } = useMarketStore();
  const [alertTarget, setAlertTarget] = useState<{ symbol: string; name: string } | null>(null);

  const symList = symbols();

  const { data: overview, refetch: refetchOverview } = useQuery({
    queryKey: ['market', 'overview'],
    queryFn: marketApi.overview,
    refetchInterval: 30000,
  });

  const { data: quoteList, isLoading, refetch: refetchQuotes } = useQuery({
    queryKey: ['market', 'watchlist', symList.join()],
    queryFn: () => marketApi.watchlistQuotes(symList),
    refetchInterval: 10000,
    enabled: symList.length > 0 && hydrated,
  });

  useEffect(() => { if (overview) setOverview(overview); }, [overview]);
  useEffect(() => { if (quoteList) setQuotes(quoteList); }, [quoteList]);

  const handleRefresh = useCallback(() => {
    refetchOverview();
    refetchQuotes();
  }, []);

  const handleAlertPress = useCallback((symbol: string, name: string) => {
    setAlertTarget({ symbol, name });
  }, []);

  const displayQuotes = symList
    .map(sym => quotes[sym] ?? quoteList?.find(q => q.symbol === sym))
    .filter(Boolean) as any[];

  if (!hydrated) return <LoadingSpinner text="加载自选股..." />;

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor={Colors.bg.primary} />

      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.title}>慧股AI</Text>
        <View style={styles.headerRight}>
          <TouchableOpacity style={styles.iconBtn} onPress={() => navigation.navigate('Search')}>
            <Text style={styles.iconText}>🔍</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.iconBtn} onPress={() => navigation.navigate('WatchlistManage')}>
            <Text style={styles.iconText}>⚙️</Text>
          </TouchableOpacity>
        </View>
      </View>

      <FlatList
        data={displayQuotes}
        keyExtractor={item => item.symbol}
        ListHeaderComponent={
          <>
            {overview && <IndexBar indices={overview.indices} />}
            {overview && <MarketStats overview={overview} />}

            <View style={styles.sectionHeader}>
              <Text style={styles.sectionTitle}>我的自选 ({stocks.length})</Text>
              <TouchableOpacity onPress={() => navigation.navigate('Search')}>
                <Text style={styles.addBtn}>+ 添加</Text>
              </TouchableOpacity>
            </View>
          </>
        }
        renderItem={({ item }) => {
          const stockMeta = stocks.find(s => s.symbol === item.symbol);
          return (
            <StockCard
              quote={item}
              onPress={() => navigation.navigate('StockDetail', { symbol: item.symbol, name: item.name })}
              onAlertPress={() => handleAlertPress(item.symbol, item.name)}
            />
          );
        }}
        refreshControl={
          <RefreshControl
            refreshing={false}
            onRefresh={handleRefresh}
            tintColor={Colors.brand.primary}
          />
        }
        ListEmptyComponent={
          isLoading ? (
            <LoadingSpinner text="加载行情..." />
          ) : (
            <View style={styles.empty}>
              <Text style={styles.emptyText}>暂无自选股</Text>
              <TouchableOpacity style={styles.emptyBtn} onPress={() => navigation.navigate('Search')}>
                <Text style={styles.emptyBtnText}>添加自选股</Text>
              </TouchableOpacity>
            </View>
          )
        }
      />

      {/* Alert config sheet */}
      {alertTarget && (
        <AlertConfigSheet
          visible={!!alertTarget}
          symbol={alertTarget.symbol}
          name={alertTarget.name}
          quote={quotes[alertTarget.symbol]}
          onClose={() => setAlertTarget(null)}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg.primary },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: Spacing.lg,
    paddingTop: 50,
    paddingBottom: Spacing.md,
    backgroundColor: Colors.bg.primary,
  },
  title: { color: Colors.brand.primary, fontSize: 22, fontWeight: '800', letterSpacing: 0.5 },
  headerRight: { flexDirection: 'row', gap: Spacing.sm },
  iconBtn: {
    width: 36, height: 36,
    backgroundColor: Colors.bg.elevated,
    borderRadius: 18,
    justifyContent: 'center',
    alignItems: 'center',
  },
  iconText: { fontSize: 15 },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
    backgroundColor: Colors.bg.primary,
  },
  sectionTitle: { color: Colors.text.primary, fontSize: 15, fontWeight: '700' },
  addBtn: { color: Colors.brand.primary, fontSize: 14 },
  empty: { padding: 40, alignItems: 'center', gap: 12 },
  emptyText: { color: Colors.text.muted, fontSize: 15 },
  emptyBtn: {
    backgroundColor: Colors.brand.primary,
    paddingHorizontal: 24, paddingVertical: 10,
    borderRadius: Radius.full,
  },
  emptyBtnText: { color: Colors.text.inverse, fontWeight: '700', fontSize: 14 },
});
