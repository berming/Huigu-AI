import React, { useState } from 'react';
import {
  View, Text, StyleSheet, FlatList, TouchableOpacity,
  StatusBar, TextInput
} from 'react-native';
import { useQuery } from '@tanstack/react-query';
import { Colors, Spacing, Radius } from '../../constants/theme';
import { sentimentApi } from '../../services/api';
import { useWatchlistStore } from '../../store/watchlist';
import { SentimentGauge } from '../../components/sentiment/SentimentGauge';
import { SocialPostCard } from '../../components/sentiment/SocialPostCard';
import { InfluencerCard } from '../../components/sentiment/InfluencerCard';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';

type SubTab = 'posts' | 'influencers';

interface Props {
  navigation: any;
}

export function SentimentScreen({ navigation }: Props) {
  const { symbols, names } = useWatchlistStore();
  const [selectedSymbol, setSelectedSymbol] = useState(symbols[0] ?? '600519');
  const selectedName = names[selectedSymbol] ?? selectedSymbol;
  const [subTab, setSubTab] = useState<SubTab>('posts');

  const { data: score, isLoading: scoreLoading } = useQuery({
    queryKey: ['sentiment-score', selectedSymbol],
    queryFn: () => sentimentApi.score(selectedSymbol, selectedName),
    refetchInterval: 60000,
  });

  const { data: posts, isLoading: postsLoading } = useQuery({
    queryKey: ['posts', selectedSymbol],
    queryFn: () => sentimentApi.posts(selectedSymbol, selectedName, 30),
    enabled: subTab === 'posts',
    refetchInterval: 120000,
  });

  const { data: influencers } = useQuery({
    queryKey: ['influencers', selectedSymbol],
    queryFn: () => sentimentApi.influencers(selectedSymbol, selectedName),
    enabled: subTab === 'influencers',
  });

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" />

      <View style={styles.header}>
        <Text style={styles.title}>社区热议</Text>
      </View>

      {/* Stock selector */}
      <View style={styles.stockSelector}>
        <FlatList
          horizontal
          showsHorizontalScrollIndicator={false}
          data={symbols}
          keyExtractor={s => s}
          contentContainerStyle={styles.selectorContent}
          renderItem={({ item }) => (
            <TouchableOpacity
              style={[styles.selectorItem, item === selectedSymbol && styles.selectorItemActive]}
              onPress={() => setSelectedSymbol(item)}
            >
              <Text style={[styles.selectorText, item === selectedSymbol && styles.selectorTextActive]}>
                {names[item] ?? item}
              </Text>
            </TouchableOpacity>
          )}
        />
      </View>

      {/* Sentiment gauge */}
      {scoreLoading ? (
        <LoadingSpinner text="加载情绪数据..." />
      ) : score ? (
        <FlatList
          data={subTab === 'posts' ? (posts ?? []) : (influencers ?? [])}
          keyExtractor={(item: any) => item.id ?? item.symbol}
          ListHeaderComponent={
            <>
              <SentimentGauge score={score} />

              {/* Sub-tabs */}
              <View style={styles.subTabs}>
                <TouchableOpacity
                  style={[styles.subTab, subTab === 'posts' && styles.subTabActive]}
                  onPress={() => setSubTab('posts')}
                >
                  <Text style={[styles.subTabText, subTab === 'posts' && styles.subTabTextActive]}>
                    最新讨论
                  </Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.subTab, subTab === 'influencers' && styles.subTabActive]}
                  onPress={() => setSubTab('influencers')}
                >
                  <Text style={[styles.subTabText, subTab === 'influencers' && styles.subTabTextActive]}>
                    达人榜
                  </Text>
                </TouchableOpacity>
              </View>
            </>
          }
          renderItem={({ item, index }: any) => {
            if (subTab === 'posts') {
              return (
                <TouchableOpacity
                  onPress={() => navigation.navigate('StockDetail', { symbol: selectedSymbol, name: selectedName })}
                >
                  <SocialPostCard post={item} />
                </TouchableOpacity>
              );
            }
            return <InfluencerCard influencer={item} rank={index + 1} />;
          }}
          ListEmptyComponent={
            postsLoading ? <LoadingSpinner text="加载帖子..." /> : (
              <View style={styles.empty}>
                <Text style={styles.emptyText}>暂无数据</Text>
              </View>
            )
          }
        />
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg.primary },
  header: {
    paddingTop: 50,
    paddingHorizontal: Spacing.lg,
    paddingBottom: Spacing.md,
    backgroundColor: Colors.bg.primary,
  },
  title: { color: Colors.text.primary, fontSize: 22, fontWeight: '800' },
  stockSelector: {
    backgroundColor: Colors.bg.secondary,
    borderBottomWidth: 1,
    borderBottomColor: Colors.bg.border,
  },
  selectorContent: { paddingHorizontal: Spacing.md, paddingVertical: Spacing.sm, gap: Spacing.sm },
  selectorItem: {
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: Radius.full,
    backgroundColor: Colors.bg.elevated,
  },
  selectorItemActive: { backgroundColor: Colors.brand.primary },
  selectorText: { color: Colors.text.secondary, fontSize: 13 },
  selectorTextActive: { color: Colors.text.inverse, fontWeight: '700' },
  subTabs: {
    flexDirection: 'row',
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
    gap: Spacing.md,
  },
  subTab: {
    paddingHorizontal: 16,
    paddingVertical: 6,
    borderRadius: Radius.full,
    borderWidth: 1,
    borderColor: Colors.bg.border,
  },
  subTabActive: { borderColor: Colors.brand.primary, backgroundColor: 'rgba(240,180,41,0.1)' },
  subTabText: { color: Colors.text.secondary, fontSize: 13 },
  subTabTextActive: { color: Colors.brand.primary, fontWeight: '600' },
  empty: { padding: 40, alignItems: 'center' },
  emptyText: { color: Colors.text.muted, fontSize: 15 },
});
