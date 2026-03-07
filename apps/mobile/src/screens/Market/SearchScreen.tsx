import React, { useState, useCallback } from 'react';
import {
  View, Text, StyleSheet, TextInput, FlatList,
  TouchableOpacity, ActivityIndicator
} from 'react-native';
import { useQuery } from '@tanstack/react-query';
import { Colors, Spacing, Radius } from '../../constants/theme';
import { marketApi, StockSearchResult } from '../../services/api';
import { useWatchlistStore } from '../../store/watchlist';

interface Props {
  navigation: any;
}

export function SearchScreen({ navigation }: Props) {
  const [query, setQuery] = useState('');
  const { addStock, removeStock, isWatched } = useWatchlistStore();

  const { data: results, isLoading } = useQuery({
    queryKey: ['search', query],
    queryFn: () => marketApi.search(query),
    enabled: query.length >= 1,
    staleTime: 30000,
  });

  const handleSelect = (item: StockSearchResult) => {
    navigation.navigate('StockDetail', { symbol: item.symbol, name: item.name });
  };

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <Text style={styles.back}>取消</Text>
        </TouchableOpacity>
        <View style={styles.searchBar}>
          <Text style={styles.searchIcon}>🔍</Text>
          <TextInput
            style={styles.input}
            placeholder="输入股票代码或名称"
            placeholderTextColor={Colors.text.muted}
            value={query}
            onChangeText={setQuery}
            autoFocus
            returnKeyType="search"
          />
          {query.length > 0 && (
            <TouchableOpacity onPress={() => setQuery('')}>
              <Text style={styles.clear}>✕</Text>
            </TouchableOpacity>
          )}
        </View>
      </View>

      {isLoading && (
        <View style={styles.loadingRow}>
          <ActivityIndicator color={Colors.brand.primary} />
          <Text style={styles.loadingText}>搜索中...</Text>
        </View>
      )}

      <FlatList
        data={results ?? []}
        keyExtractor={item => item.symbol}
        renderItem={({ item }) => {
          const watched = isWatched(item.symbol);
          return (
            <TouchableOpacity style={styles.resultItem} onPress={() => handleSelect(item)}>
              <View style={styles.resultLeft}>
                <Text style={styles.resultCode}>{item.symbol}</Text>
                <Text style={styles.resultName}>{item.name}</Text>
              </View>
              <View style={styles.resultRight}>
                <Text style={styles.resultMarket}>{item.market}</Text>
                <TouchableOpacity
                  style={[styles.watchBtn, watched && styles.watchBtnActive]}
                  onPress={() => watched ? removeStock(item.symbol) : addStock(item.symbol, item.name)}
                >
                  <Text style={[styles.watchBtnText, watched && styles.watchBtnTextActive]}>
                    {watched ? '已自选' : '+ 自选'}
                  </Text>
                </TouchableOpacity>
              </View>
            </TouchableOpacity>
          );
        }}
        ListEmptyComponent={
          query.length > 0 && !isLoading ? (
            <View style={styles.empty}>
              <Text style={styles.emptyText}>未找到相关股票</Text>
            </View>
          ) : null
        }
      />
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
    gap: Spacing.md,
  },
  back: { color: Colors.brand.primary, fontSize: 15 },
  searchBar: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.bg.elevated,
    borderRadius: Radius.full,
    paddingHorizontal: 12,
    gap: 6,
  },
  searchIcon: { fontSize: 13 },
  input: { flex: 1, color: Colors.text.primary, fontSize: 15, paddingVertical: 9 },
  clear: { color: Colors.text.muted, fontSize: 14, padding: 4 },
  loadingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    padding: Spacing.lg,
  },
  loadingText: { color: Colors.text.secondary, fontSize: 14 },
  resultItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
    borderBottomWidth: 0.5,
    borderBottomColor: Colors.bg.border,
  },
  resultLeft: {},
  resultCode: { color: Colors.text.primary, fontSize: 15, fontWeight: '700' },
  resultName: { color: Colors.text.secondary, fontSize: 13, marginTop: 2 },
  resultRight: { flexDirection: 'row', alignItems: 'center', gap: Spacing.md },
  resultMarket: {
    color: Colors.text.muted,
    fontSize: 11,
    backgroundColor: Colors.bg.elevated,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: Radius.sm,
  },
  watchBtn: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: Radius.full,
    borderWidth: 1,
    borderColor: Colors.brand.primary,
  },
  watchBtnActive: { backgroundColor: Colors.brand.primary },
  watchBtnText: { color: Colors.brand.primary, fontSize: 12 },
  watchBtnTextActive: { color: Colors.text.inverse },
  empty: { padding: 40, alignItems: 'center' },
  emptyText: { color: Colors.text.muted, fontSize: 15 },
});
