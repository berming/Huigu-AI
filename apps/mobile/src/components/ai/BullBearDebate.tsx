import React from 'react';
import { View, Text, StyleSheet, ScrollView } from 'react-native';
import { Colors, Spacing, Radius } from '../../constants/theme';
import { BullBearDebate as DebateData, DebateArgument } from '../../services/api';

interface Props {
  debate: DebateData;
}

function StrengthDots({ strength }: { strength: number }) {
  return (
    <View style={styles.dots}>
      {[1, 2, 3, 4, 5].map(i => (
        <View key={i} style={[styles.dot, i <= strength && styles.dotFilled]} />
      ))}
    </View>
  );
}

function ArgumentItem({ arg, side }: { arg: DebateArgument; side: 'bull' | 'bear' }) {
  const color = side === 'bull' ? Colors.market.up : Colors.market.down;
  return (
    <View style={[styles.argItem, { borderLeftColor: color }]}>
      <View style={styles.argHeader}>
        <Text style={[styles.argPoint, { color }]}>{arg.point}</Text>
        <StrengthDots strength={arg.strength} />
      </View>
      <Text style={styles.argEvidence}>{arg.evidence}</Text>
    </View>
  );
}

export function BullBearDebateCard({ debate }: Props) {
  const bearRatio = 100 - debate.bull_ratio;

  return (
    <View style={styles.container}>
      {/* Ratio bar */}
      <View style={styles.ratioSection}>
        <Text style={[styles.ratioLabel, { color: Colors.market.up }]}>
          多 {Math.round(debate.bull_ratio)}%
        </Text>
        <View style={styles.ratioBar}>
          <View style={[styles.ratioFill, { flex: debate.bull_ratio / 100, backgroundColor: Colors.market.up }]} />
          <View style={[styles.ratioFill, { flex: bearRatio / 100, backgroundColor: Colors.market.down }]} />
        </View>
        <Text style={[styles.ratioLabel, { color: Colors.market.down }]}>
          空 {Math.round(bearRatio)}%
        </Text>
      </View>

      {/* Two-column debate */}
      <View style={styles.debateColumns}>
        <View style={styles.column}>
          <Text style={[styles.columnHeader, { color: Colors.market.up }]}>📈 多方论点</Text>
          {debate.bull_arguments.map((arg, i) => (
            <ArgumentItem key={i} arg={arg} side="bull" />
          ))}
        </View>

        <View style={styles.divider} />

        <View style={styles.column}>
          <Text style={[styles.columnHeader, { color: Colors.market.down }]}>📉 空方论点</Text>
          {debate.bear_arguments.map((arg, i) => (
            <ArgumentItem key={i} arg={arg} side="bear" />
          ))}
        </View>
      </View>

      {/* Opportunities */}
      {debate.key_opportunities.length > 0 && (
        <View style={[styles.section, styles.opportunitySection]}>
          <Text style={styles.sectionTitle}>🟢 核心机会</Text>
          {debate.key_opportunities.map((o, i) => (
            <Text key={i} style={[styles.bullet, { color: Colors.opportunity }]}>• {o}</Text>
          ))}
        </View>
      )}

      {/* Risks */}
      {debate.key_risks.length > 0 && (
        <View style={[styles.section, styles.riskSection]}>
          <Text style={styles.sectionTitle}>🔴 风险提示</Text>
          {debate.key_risks.map((r, i) => (
            <Text key={i} style={[styles.bullet, { color: Colors.risk }]}>• {r}</Text>
          ))}
        </View>
      )}

      {/* AI Summary */}
      <View style={styles.summarySection}>
        <Text style={styles.summaryLabel}>🤖 AI综合研判</Text>
        <Text style={styles.summaryText}>{debate.ai_summary}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { paddingVertical: Spacing.sm },
  ratioSection: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: Spacing.lg,
    gap: Spacing.sm,
    marginBottom: Spacing.lg,
  },
  ratioLabel: { fontSize: 12, fontWeight: '700', width: 52 },
  ratioBar: {
    flex: 1,
    height: 8,
    borderRadius: Radius.full,
    flexDirection: 'row',
    overflow: 'hidden',
    gap: 2,
  },
  ratioFill: { borderRadius: Radius.full },
  debateColumns: {
    flexDirection: 'row',
    paddingHorizontal: Spacing.lg,
    gap: Spacing.md,
    marginBottom: Spacing.lg,
  },
  column: { flex: 1 },
  columnHeader: { fontSize: 13, fontWeight: '700', marginBottom: Spacing.sm },
  divider: { width: 1, backgroundColor: Colors.bg.border },
  argItem: {
    borderLeftWidth: 2,
    paddingLeft: Spacing.sm,
    marginBottom: Spacing.md,
  },
  argHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 3 },
  argPoint: { fontSize: 12, fontWeight: '600', flex: 1 },
  argEvidence: { color: Colors.text.muted, fontSize: 11, lineHeight: 15 },
  dots: { flexDirection: 'row', gap: 2 },
  dot: { width: 5, height: 5, borderRadius: 3, backgroundColor: Colors.bg.border },
  dotFilled: { backgroundColor: Colors.brand.primary },
  section: {
    marginHorizontal: Spacing.lg,
    padding: Spacing.md,
    borderRadius: Radius.md,
    marginBottom: Spacing.sm,
  },
  opportunitySection: { backgroundColor: 'rgba(38,161,123,0.1)', borderWidth: 1, borderColor: 'rgba(38,161,123,0.3)' },
  riskSection: { backgroundColor: 'rgba(248,73,96,0.1)', borderWidth: 1, borderColor: 'rgba(248,73,96,0.3)' },
  sectionTitle: { fontSize: 12, fontWeight: '700', color: Colors.text.primary, marginBottom: Spacing.xs },
  bullet: { fontSize: 12, lineHeight: 18 },
  summarySection: {
    marginHorizontal: Spacing.lg,
    padding: Spacing.md,
    backgroundColor: Colors.bg.card,
    borderRadius: Radius.md,
    borderWidth: 1,
    borderColor: Colors.ai.purple + '40',
    marginBottom: Spacing.sm,
  },
  summaryLabel: { color: Colors.ai.purple, fontSize: 12, fontWeight: '700', marginBottom: Spacing.sm },
  summaryText: { color: Colors.text.secondary, fontSize: 13, lineHeight: 20 },
});
