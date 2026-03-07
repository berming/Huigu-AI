import React from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity, StatusBar
} from 'react-native';
import { Colors, Spacing, Radius } from '../../constants/theme';

const INVESTOR_TYPES = [
  { label: '长线价投', icon: '📈', desc: '关注基本面，持股周期长', active: true },
  { label: '短线打板', icon: '⚡', desc: '追涨停板，快进快出', active: false },
  { label: '技术派', icon: '📊', desc: '以技术指标为主要决策依据', active: false },
];

const MENU_ITEMS = [
  { icon: '🔔', label: '价格提醒', sub: '设置涨跌提醒' },
  { icon: '📋', label: '模拟交易', sub: '纸上交易练习' },
  { icon: '📰', label: '研报库', sub: '近期精选研报' },
  { icon: '⚙️', label: '设置', sub: '账户与偏好设置' },
  { icon: '❓', label: '帮助与反馈', sub: '联系我们' },
];

export function ProfileScreen() {
  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" />

      <ScrollView showsVerticalScrollIndicator={false}>
        {/* Avatar section */}
        <View style={styles.hero}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>慧</Text>
          </View>
          <Text style={styles.username}>慧股AI用户</Text>
          <Text style={styles.subtitle}>智慧投资，理性决策</Text>
        </View>

        {/* Investor type */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>投资风格</Text>
          <View style={styles.typeGrid}>
            {INVESTOR_TYPES.map(type => (
              <TouchableOpacity
                key={type.label}
                style={[styles.typeCard, type.active && styles.typeCardActive]}
              >
                <Text style={styles.typeIcon}>{type.icon}</Text>
                <Text style={[styles.typeLabel, type.active && styles.typeLabelActive]}>
                  {type.label}
                </Text>
                <Text style={styles.typeDesc}>{type.desc}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* Stats */}
        <View style={styles.statsRow}>
          <View style={styles.statCard}>
            <Text style={styles.statValue}>6</Text>
            <Text style={styles.statLabel}>自选股</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.statCard}>
            <Text style={[styles.statValue, { color: Colors.market.up }]}>+12.3%</Text>
            <Text style={styles.statLabel}>模拟收益</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.statCard}>
            <Text style={styles.statValue}>28</Text>
            <Text style={styles.statLabel}>AI分析次数</Text>
          </View>
        </View>

        {/* Menu */}
        <View style={styles.section}>
          {MENU_ITEMS.map(item => (
            <TouchableOpacity key={item.label} style={styles.menuItem}>
              <Text style={styles.menuIcon}>{item.icon}</Text>
              <View style={styles.menuText}>
                <Text style={styles.menuLabel}>{item.label}</Text>
                <Text style={styles.menuSub}>{item.sub}</Text>
              </View>
              <Text style={styles.menuArrow}>›</Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Disclaimer */}
        <View style={styles.disclaimer}>
          <Text style={styles.disclaimerText}>
            慧股AI — 您的智能投研助手{'\n'}
            所有AI生成内容仅供参考，不构成投资建议{'\n'}
            投资有风险，入市须谨慎
          </Text>
          <Text style={styles.version}>v1.0.0</Text>
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg.primary },
  hero: {
    alignItems: 'center',
    paddingTop: 60,
    paddingBottom: Spacing.xl,
  },
  avatar: {
    width: 80, height: 80,
    borderRadius: 40,
    backgroundColor: Colors.brand.primary,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: Spacing.md,
    shadowColor: Colors.brand.primary,
    shadowOpacity: 0.4,
    shadowRadius: 15,
    elevation: 10,
  },
  avatarText: { color: Colors.bg.primary, fontSize: 32, fontWeight: '900' },
  username: { color: Colors.text.primary, fontSize: 18, fontWeight: '700', marginBottom: 4 },
  subtitle: { color: Colors.text.secondary, fontSize: 13 },
  section: { marginBottom: Spacing.xl },
  sectionTitle: {
    color: Colors.text.primary,
    fontSize: 15,
    fontWeight: '700',
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
  },
  typeGrid: {
    flexDirection: 'row',
    paddingHorizontal: Spacing.lg,
    gap: Spacing.sm,
  },
  typeCard: {
    flex: 1,
    backgroundColor: Colors.bg.card,
    borderRadius: Radius.md,
    padding: Spacing.md,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: Colors.bg.border,
  },
  typeCardActive: {
    borderColor: Colors.brand.primary,
    backgroundColor: 'rgba(240,180,41,0.1)',
  },
  typeIcon: { fontSize: 22, marginBottom: 4 },
  typeLabel: { color: Colors.text.secondary, fontSize: 12, fontWeight: '600', marginBottom: 2 },
  typeLabelActive: { color: Colors.brand.primary },
  typeDesc: { color: Colors.text.muted, fontSize: 9, textAlign: 'center' },
  statsRow: {
    flexDirection: 'row',
    backgroundColor: Colors.bg.card,
    marginHorizontal: Spacing.lg,
    borderRadius: Radius.lg,
    padding: Spacing.lg,
    marginBottom: Spacing.xl,
  },
  statCard: { flex: 1, alignItems: 'center' },
  statValue: { color: Colors.text.primary, fontSize: 20, fontWeight: '700', marginBottom: 4 },
  statLabel: { color: Colors.text.muted, fontSize: 11 },
  statDivider: { width: 1, backgroundColor: Colors.bg.border, marginHorizontal: Spacing.md },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
    gap: Spacing.md,
    borderBottomWidth: 0.5,
    borderBottomColor: Colors.bg.border,
  },
  menuIcon: { fontSize: 20, width: 28 },
  menuText: { flex: 1 },
  menuLabel: { color: Colors.text.primary, fontSize: 14, fontWeight: '500' },
  menuSub: { color: Colors.text.muted, fontSize: 11, marginTop: 2 },
  menuArrow: { color: Colors.text.muted, fontSize: 18 },
  disclaimer: { padding: Spacing.xl, alignItems: 'center', gap: Spacing.sm },
  disclaimerText: { color: Colors.text.muted, fontSize: 11, textAlign: 'center', lineHeight: 18 },
  version: { color: Colors.text.muted, fontSize: 10 },
});
