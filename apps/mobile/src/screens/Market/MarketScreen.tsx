import React, { useCallback } from 'react';
import {
  View, Text, StyleSheet, FlatList, TextInput,
  TouchableOpacity, RefreshControl, StatusBar
} from 'react-native';
import { useQuery } from '@tanstack/react-query';
import { Colors, Spacing, Radius } from '../../constants/theme';
import { marketApi } from '../../services/api';
import { useWatchlistStore } from '../../store/watchlist';
import { IndexBar } from '../../components/market/IndexBar';
import { MarketStats } from '../../components/market/MarketStats';
import { StockCard } from '../../components/market/StockCard';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';

interface Props {
  navigation: any;
}

export function MarketScreen({ navigation }: Props) {
  const { symbols, names } = useWatchlistStore();

  const { data: overview, refetch: refetchOverview } = useQuery({
    queryKey: ['market', 'overview'],
    queryFn: marketApi.overview,
    refetchInterval: 30000,
  });

  const { data: quotes, isLoading, refetch: refetchQuotes } = useQuery({
    queryKey: ['market', 'watchlist', symbols],
    queryFn: () => marketApi.watchlistQuotes(symbols),
    refetchInterval: 15000,
    enabled: symbols.length > 0,
  });

  const handleRefresh = useCallback(() => {
    refetchOverview();
    refetchQuotes();
  }, []);

  const handleStockPress = useCallback((symbol: string, name: string) => {
    navigation.navigate('StockDetail', { symbol, name });
  }, [navigation]);

  if (isLoading && !quotes) {
    return <LoadingSpinner text="加载行情数据..." />;
  }

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor={Colors.bg.primary} />

      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.title}>慧股AI</Text>
        <TouchableOpacity
          style={styles.searchBtn}
          onPress={() => navigation.navigate('Search')}
        >
          <Text style={styles.searchIcon}>🔍</Text>
          <Text style={styles.searchText}>搜索股票</Text>
        </TouchableOpacity>
      </View>

      <FlatList
        data={quotes ?? []}
        keyExtractor={item => item.symbol}
        ListHeaderComponent={
          <>
            {overview && <IndexBar indices={overview.indices} />}
            {overview && <MarketStats overview={overview} />}
            <View style={styles.sectionHeader}>
              <Text style={styles.sectionTitle}>我的自选</Text>
              <TouchableOpacity onPress={() => navigation.navigate('Search')}>
                <Text style={styles.addBtn}>+ 添加</Text>
              </TouchableOpacity>
            </View>
          </>
        }
        renderItem={({ item }) => (
          <StockCard
            quote={item}
            onPress={() => handleStockPress(item.symbol, item.name)}
          />
        )}
        refreshControl={
          <RefreshControl
            refreshing={false}
            onRefresh={handleRefresh}
            tintColor={Colors.brand.primary}
          />
        }
        ListEmptyComponent={
          <View style={styles.empty}>
            <Text style={styles.emptyText}>暂无自选股</Text>
            <TouchableOpacity
              style={styles.emptyBtn}
              onPress={() => navigation.navigate('Search')}
            >
              <Text style={styles.emptyBtnText}>添加自选股</Text>
            </TouchableOpacity>
          </View>
        }
      />
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
  title: {
    color: Colors.brand.primary,
    fontSize: 22,
    fontWeight: '800',
    letterSpacing: 0.5,
  },
  searchBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.bg.elevated,
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: Radius.full,
    gap: 6,
  },
  searchIcon: { fontSize: 13 },
  searchText: { color: Colors.text.secondary, fontSize: 13 },
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
    paddingHorizontal: 24,
    paddingVertical: 10,
    borderRadius: Radius.full,
  },
  emptyBtnText: { color: Colors.text.inverse, fontWeight: '700', fontSize: 14 },
});
