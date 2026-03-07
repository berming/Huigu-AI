import React, { useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity,
  FlatList, StatusBar, Alert
} from 'react-native';
import { useQuery } from '@tanstack/react-query';
import { Colors, Spacing, Radius } from '../../constants/theme';
import { aiApi, marketApi } from '../../services/api';
import { useWatchlistStore } from '../../store/watchlist';
import { AIStreamCard } from '../../components/ai/AIStreamCard';
import { BullBearDebateCard } from '../../components/ai/BullBearDebate';
import { DisclaimerBanner } from '../../components/common/DisclaimerBanner';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';

// Hot concepts for demo
const HOT_CONCEPTS = [
  { name: '低空经济', heat: 95, description: '航空管理局放开低空空域，eVTOL产业链快速崛起', icon: '🚁' },
  { name: 'AI算力', heat: 92, description: 'DeepSeek引爆国产大模型需求，算力基础设施加速扩容', icon: '🖥️' },
  { name: '人形机器人', heat: 88, description: '特斯拉Optimus量产节点临近，国内产业链配套成熟', icon: '🤖' },
  { name: '合成生物', heat: 75, description: '政策扶持+技术突破，生物制造产业迎来战略机遇期', icon: '🧬' },
  { name: '核电重启', heat: 72, description: '国家核电发展规划加速，新建核电项目审批提速', icon: '⚛️' },
];

interface Props {
  navigation: any;
}

export function ResearchScreen({ navigation }: Props) {
  const { symbols, names } = useWatchlistStore();
  const [selectedSymbol, setSelectedSymbol] = useState(symbols[0] ?? '600519');
  const selectedName = names[selectedSymbol] ?? selectedSymbol;
  const [showDebate, setShowDebate] = useState(false);
  const [debateLoaded, setDebateLoaded] = useState(false);

  const { data: debate, isFetching: debateFetching, refetch: fetchDebate } = useQuery({
    queryKey: ['debate', selectedSymbol],
    queryFn: () => aiApi.debate(selectedSymbol, selectedName),
    enabled: false,
  });

  const handleDebate = async () => {
    setShowDebate(true);
    setDebateLoaded(false);
    await fetchDebate();
    setDebateLoaded(true);
  };

  const handleConceptPress = (concept: typeof HOT_CONCEPTS[0]) => {
    Alert.alert(
      `${concept.icon} ${concept.name}`,
      concept.description + '\n\n热度: ' + concept.heat + '/100',
      [{ text: '关闭' }]
    );
  };

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" />

      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.title}>AI投研</Text>
        <View style={styles.aiTag}>
          <Text style={styles.aiTagText}>⚡ Claude驱动</Text>
        </View>
      </View>

      <ScrollView showsVerticalScrollIndicator={false}>

        {/* Stock selector */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>选择研究标的</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.symbolScroll}>
            {symbols.map(sym => (
              <TouchableOpacity
                key={sym}
                style={[styles.symbolChip, sym === selectedSymbol && styles.symbolChipActive]}
                onPress={() => {
                  setSelectedSymbol(sym);
                  setShowDebate(false);
                }}
              >
                <Text style={[styles.symbolChipText, sym === selectedSymbol && styles.symbolChipTextActive]}>
                  {names[sym] ?? sym}
                </Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        </View>

        {/* AI streaming analysis */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>🤖 智能分析</Text>
          <AIStreamCard
            key={selectedSymbol}
            url={aiApi.analyzeUrl(selectedSymbol, selectedName)}
          />
          <DisclaimerBanner />
        </View>

        {/* Bull/Bear debate */}
        <View style={styles.section}>
          <View style={styles.debateHeader}>
            <Text style={styles.sectionTitle}>⚔️ 多空辩论室</Text>
            {!showDebate && (
              <TouchableOpacity style={styles.debateBtn} onPress={handleDebate}>
                <Text style={styles.debateBtnText}>生成辩论</Text>
              </TouchableOpacity>
            )}
          </View>

          {showDebate && debateFetching && <LoadingSpinner text="AI正在生成多空辩论..." />}
          {showDebate && debate && <BullBearDebateCard debate={debate} />}
        </View>

        {/* Hot concepts */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>🔥 热点概念追踪</Text>
          {HOT_CONCEPTS.map(concept => (
            <TouchableOpacity
              key={concept.name}
              style={styles.conceptCard}
              onPress={() => handleConceptPress(concept)}
            >
              <View style={styles.conceptLeft}>
                <Text style={styles.conceptIcon}>{concept.icon}</Text>
                <View>
                  <Text style={styles.conceptName}>{concept.name}</Text>
                  <Text style={styles.conceptDesc} numberOfLines={1}>{concept.description}</Text>
                </View>
              </View>
              <View style={styles.conceptHeat}>
                <Text style={styles.conceptHeatValue}>{concept.heat}</Text>
                <Text style={styles.conceptHeatLabel}>热度</Text>
                <View style={styles.heatBar}>
                  <View style={[styles.heatFill, { width: `${concept.heat}%` }]} />
                </View>
              </View>
            </TouchableOpacity>
          ))}
        </View>

        <View style={{ height: 100 }} />
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg.primary },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: 50,
    paddingHorizontal: Spacing.lg,
    paddingBottom: Spacing.md,
  },
  title: { color: Colors.text.primary, fontSize: 22, fontWeight: '800' },
  aiTag: {
    backgroundColor: Colors.ai.purple + '25',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: Radius.full,
    borderWidth: 1,
    borderColor: Colors.ai.purple + '60',
  },
  aiTagText: { color: Colors.ai.purple, fontSize: 11, fontWeight: '600' },
  section: { marginBottom: Spacing.lg },
  sectionTitle: {
    color: Colors.text.primary,
    fontSize: 16,
    fontWeight: '700',
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
  },
  symbolScroll: { paddingHorizontal: Spacing.lg },
  symbolChip: {
    paddingHorizontal: 14,
    paddingVertical: 7,
    borderRadius: Radius.full,
    backgroundColor: Colors.bg.elevated,
    marginRight: Spacing.sm,
  },
  symbolChipActive: { backgroundColor: Colors.brand.primary },
  symbolChipText: { color: Colors.text.secondary, fontSize: 13 },
  symbolChipTextActive: { color: Colors.text.inverse, fontWeight: '700' },
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
  conceptCard: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: Colors.bg.card,
    marginHorizontal: Spacing.lg,
    marginBottom: Spacing.sm,
    padding: Spacing.md,
    borderRadius: Radius.md,
    borderWidth: 0.5,
    borderColor: Colors.bg.border,
  },
  conceptLeft: { flexDirection: 'row', alignItems: 'center', gap: Spacing.md, flex: 1 },
  conceptIcon: { fontSize: 24 },
  conceptName: { color: Colors.text.primary, fontSize: 14, fontWeight: '600', marginBottom: 3 },
  conceptDesc: { color: Colors.text.muted, fontSize: 11 },
  conceptHeat: { alignItems: 'flex-end', width: 60 },
  conceptHeatValue: { color: Colors.brand.primary, fontSize: 18, fontWeight: '700' },
  conceptHeatLabel: { color: Colors.text.muted, fontSize: 9, marginBottom: 4 },
  heatBar: {
    width: 50, height: 4, backgroundColor: Colors.bg.border,
    borderRadius: Radius.full, overflow: 'hidden',
  },
  heatFill: { height: '100%', backgroundColor: Colors.brand.primary, borderRadius: Radius.full },
});
