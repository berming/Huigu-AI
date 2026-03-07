/**
 * Watchlist management screen.
 * Features:
 *  - View all watched stocks grouped by custom label
 *  - Drag reorder (up/down buttons — no external lib needed)
 *  - Assign / rename groups
 *  - Delete stocks with swipe-like confirm
 *  - Add personal notes per stock
 *  - Quick entry to alert config
 */
import React, { useState } from 'react';
import {
  View, Text, StyleSheet, FlatList, TouchableOpacity,
  TextInput, Alert, StatusBar, Modal, ScrollView,
} from 'react-native';
import { Colors, Spacing, Radius } from '../../constants/theme';
import { useWatchlistStore, WatchedStock } from '../../store/watchlist';
import { AlertConfigSheet } from '../../components/market/AlertConfigSheet';
import { useMarketStore } from '../../store/market';

const PRESET_GROUPS = ['自选', '重点关注', '长期持有', '短线观察'];

interface Props {
  navigation: any;
}

function GroupTag({ label, active, onPress }: { label: string; active: boolean; onPress: () => void }) {
  return (
    <TouchableOpacity
      style={[styles.groupTag, active && styles.groupTagActive]}
      onPress={onPress}
    >
      <Text style={[styles.groupTagText, active && styles.groupTagTextActive]}>{label}</Text>
    </TouchableOpacity>
  );
}

function StockRow({
  stock,
  index,
  total,
  onMoveUp,
  onMoveDown,
  onDelete,
  onEditGroup,
  onEditAlert,
  onEditNote,
  onPress,
}: {
  stock: WatchedStock;
  index: number;
  total: number;
  onMoveUp: () => void;
  onMoveDown: () => void;
  onDelete: () => void;
  onEditGroup: () => void;
  onEditAlert: () => void;
  onEditNote: () => void;
  onPress: () => void;
}) {
  const { quotes } = useMarketStore();
  const quote = quotes[stock.symbol];
  const hasAlert = stock.alert.enabled && (stock.alert.upperTarget || stock.alert.lowerTarget);
  const alertTriggered = stock.alert.upperTriggered || stock.alert.lowerTriggered;

  return (
    <View style={styles.stockRow}>
      {/* Reorder buttons */}
      <View style={styles.reorderCol}>
        <TouchableOpacity onPress={onMoveUp} disabled={index === 0} style={styles.reorderBtn}>
          <Text style={[styles.reorderIcon, index === 0 && styles.reorderIconDisabled]}>▲</Text>
        </TouchableOpacity>
        <Text style={styles.reorderIndex}>{index + 1}</Text>
        <TouchableOpacity onPress={onMoveDown} disabled={index === total - 1} style={styles.reorderBtn}>
          <Text style={[styles.reorderIcon, index === total - 1 && styles.reorderIconDisabled]}>▼</Text>
        </TouchableOpacity>
      </View>

      {/* Main info */}
      <TouchableOpacity style={styles.stockInfo} onPress={onPress}>
        <View style={styles.stockNameRow}>
          <Text style={styles.stockName}>{stock.name}</Text>
          <View style={[styles.groupPill, { borderColor: Colors.brand.primary + '60' }]}>
            <Text style={styles.groupPillText}>{stock.group}</Text>
          </View>
          {alertTriggered && (
            <View style={styles.alertTriggeredBadge}>
              <Text style={styles.alertTriggeredText}>提醒触发</Text>
            </View>
          )}
        </View>
        <View style={styles.stockMeta}>
          <Text style={styles.stockCode}>{stock.symbol}</Text>
          {quote && (
            <Text style={[
              styles.stockPrice,
              { color: quote.change_pct > 0 ? Colors.market.up : quote.change_pct < 0 ? Colors.market.down : Colors.market.flat }
            ]}>
              {quote.price.toFixed(2)} ({quote.change_pct > 0 ? '+' : ''}{quote.change_pct.toFixed(2)}%)
            </Text>
          )}
        </View>
        {hasAlert && (
          <Text style={styles.alertSummary}>
            🔔 {stock.alert.upperTarget ? `涨至 ${stock.alert.upperTarget}` : ''}
            {stock.alert.upperTarget && stock.alert.lowerTarget ? ' · ' : ''}
            {stock.alert.lowerTarget ? `跌至 ${stock.alert.lowerTarget}` : ''}
          </Text>
        )}
        {stock.note ? <Text style={styles.noteText}>📝 {stock.note}</Text> : null}
      </TouchableOpacity>

      {/* Action buttons */}
      <View style={styles.actionCol}>
        <TouchableOpacity style={styles.actionBtn} onPress={onEditAlert}>
          <Text style={styles.actionIcon}>🔔</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.actionBtn} onPress={onEditGroup}>
          <Text style={styles.actionIcon}>🏷️</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.actionBtn} onPress={onEditNote}>
          <Text style={styles.actionIcon}>📝</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.actionBtn} onPress={onDelete}>
          <Text style={[styles.actionIcon, { color: Colors.risk }]}>🗑️</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

export function WatchlistManageScreen({ navigation }: Props) {
  const { stocks, groups, removeStock, reorderStock, setGroup, setNote } = useWatchlistStore();
  const [filterGroup, setFilterGroup] = useState('全部');
  const [alertTarget, setAlertTarget] = useState<{ symbol: string; name: string } | null>(null);
  const { quotes } = useMarketStore();

  // Group picker modal
  const [groupModal, setGroupModal] = useState<{ symbol: string } | null>(null);
  const [customGroup, setCustomGroup] = useState('');

  // Note modal
  const [noteModal, setNoteModal] = useState<{ symbol: string; current: string } | null>(null);
  const [noteText, setNoteText] = useState('');

  const allGroups = groups();
  const filtered = filterGroup === '全部'
    ? stocks
    : stocks.filter(s => s.group === filterGroup);

  const handleDelete = (symbol: string, name: string) => {
    Alert.alert(
      `移除自选`,
      `确定将 ${name} 从自选中移除？`,
      [
        { text: '取消', style: 'cancel' },
        { text: '移除', style: 'destructive', onPress: () => removeStock(symbol) },
      ]
    );
  };

  const handleGroupSave = (symbol: string, group: string) => {
    if (!group.trim()) return;
    setGroup(symbol, group.trim());
    setGroupModal(null);
    setCustomGroup('');
  };

  const handleNoteSave = () => {
    if (noteModal) {
      setNote(noteModal.symbol, noteText.trim());
      setNoteModal(null);
    }
  };

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" />

      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
          <Text style={styles.backIcon}>‹</Text>
        </TouchableOpacity>
        <Text style={styles.title}>自选股管理</Text>
        <TouchableOpacity onPress={() => navigation.navigate('Search')} style={styles.addBtn}>
          <Text style={styles.addBtnText}>+ 添加</Text>
        </TouchableOpacity>
      </View>

      {/* Group filter tabs */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={styles.groupScroll}
        contentContainerStyle={styles.groupScrollContent}
      >
        {allGroups.map(g => (
          <GroupTag
            key={g}
            label={`${g} ${g === '全部' ? `(${stocks.length})` : `(${stocks.filter(s => s.group === g).length})`}`}
            active={filterGroup === g}
            onPress={() => setFilterGroup(g)}
          />
        ))}
      </ScrollView>

      {/* Stock list */}
      <FlatList
        data={filtered}
        keyExtractor={s => s.symbol}
        renderItem={({ item, index }) => (
          <StockRow
            stock={item}
            index={stocks.indexOf(item)}   // real index for reorder
            total={stocks.length}
            onMoveUp={() => reorderStock(item.symbol, 'up')}
            onMoveDown={() => reorderStock(item.symbol, 'down')}
            onDelete={() => handleDelete(item.symbol, item.name)}
            onEditGroup={() => setGroupModal({ symbol: item.symbol })}
            onEditAlert={() => setAlertTarget({ symbol: item.symbol, name: item.name })}
            onEditNote={() => {
              setNoteText(item.note ?? '');
              setNoteModal({ symbol: item.symbol, current: item.note ?? '' });
            }}
            onPress={() => navigation.navigate('StockDetail', { symbol: item.symbol, name: item.name })}
          />
        )}
        ListEmptyComponent={
          <View style={styles.empty}>
            <Text style={styles.emptyText}>该分组暂无自选股</Text>
            <TouchableOpacity style={styles.emptyBtn} onPress={() => navigation.navigate('Search')}>
              <Text style={styles.emptyBtnText}>去添加</Text>
            </TouchableOpacity>
          </View>
        }
        contentContainerStyle={{ paddingBottom: 40 }}
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

      {/* Group picker modal */}
      <Modal visible={!!groupModal} transparent animationType="fade" onRequestClose={() => setGroupModal(null)}>
        <TouchableOpacity style={styles.modalBackdrop} activeOpacity={1} onPress={() => setGroupModal(null)} />
        <View style={styles.modalCard}>
          <Text style={styles.modalTitle}>选择分组</Text>
          {PRESET_GROUPS.map(g => (
            <TouchableOpacity
              key={g}
              style={styles.modalOption}
              onPress={() => groupModal && handleGroupSave(groupModal.symbol, g)}
            >
              <Text style={styles.modalOptionText}>{g}</Text>
            </TouchableOpacity>
          ))}
          <View style={styles.modalDivider} />
          <TextInput
            style={styles.modalInput}
            value={customGroup}
            onChangeText={setCustomGroup}
            placeholder="自定义分组名称"
            placeholderTextColor={Colors.text.muted}
          />
          <TouchableOpacity
            style={styles.modalConfirmBtn}
            onPress={() => groupModal && handleGroupSave(groupModal.symbol, customGroup)}
          >
            <Text style={styles.modalConfirmText}>确定</Text>
          </TouchableOpacity>
        </View>
      </Modal>

      {/* Note editor modal */}
      <Modal visible={!!noteModal} transparent animationType="fade" onRequestClose={() => setNoteModal(null)}>
        <TouchableOpacity style={styles.modalBackdrop} activeOpacity={1} onPress={() => setNoteModal(null)} />
        <View style={styles.modalCard}>
          <Text style={styles.modalTitle}>添加备注</Text>
          <TextInput
            style={[styles.modalInput, styles.noteInput]}
            value={noteText}
            onChangeText={setNoteText}
            placeholder="输入个人备注（如持仓成本、买入原因等）"
            placeholderTextColor={Colors.text.muted}
            multiline
            maxLength={200}
          />
          <Text style={styles.noteCount}>{noteText.length}/200</Text>
          <TouchableOpacity style={styles.modalConfirmBtn} onPress={handleNoteSave}>
            <Text style={styles.modalConfirmText}>保存</Text>
          </TouchableOpacity>
        </View>
      </Modal>
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
  },
  backBtn: { padding: Spacing.xs },
  backIcon: { color: Colors.text.primary, fontSize: 28, lineHeight: 28 },
  title: { flex: 1, color: Colors.text.primary, fontSize: 17, fontWeight: '700', textAlign: 'center' },
  addBtn: {
    paddingHorizontal: 12, paddingVertical: 5,
    backgroundColor: Colors.brand.primary,
    borderRadius: Radius.full,
  },
  addBtnText: { color: Colors.bg.primary, fontSize: 12, fontWeight: '700' },
  groupScroll: {
    backgroundColor: Colors.bg.secondary,
    borderBottomWidth: 1,
    borderBottomColor: Colors.bg.border,
  },
  groupScrollContent: { paddingHorizontal: Spacing.md, paddingVertical: Spacing.sm, gap: Spacing.sm },
  groupTag: {
    paddingHorizontal: 12, paddingVertical: 5,
    backgroundColor: Colors.bg.elevated,
    borderRadius: Radius.full,
  },
  groupTagActive: { backgroundColor: Colors.brand.primary },
  groupTagText: { color: Colors.text.secondary, fontSize: 12 },
  groupTagTextActive: { color: Colors.bg.primary, fontWeight: '700' },
  stockRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.bg.secondary,
    borderBottomWidth: 0.5,
    borderBottomColor: Colors.bg.border,
    paddingVertical: Spacing.sm,
  },
  reorderCol: { width: 32, alignItems: 'center', paddingHorizontal: Spacing.xs },
  reorderBtn: { padding: 4 },
  reorderIcon: { color: Colors.text.secondary, fontSize: 10 },
  reorderIconDisabled: { color: Colors.text.muted, opacity: 0.3 },
  reorderIndex: { color: Colors.text.muted, fontSize: 10, marginVertical: 2 },
  stockInfo: { flex: 1, paddingVertical: Spacing.xs },
  stockNameRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 3 },
  stockName: { color: Colors.text.primary, fontSize: 14, fontWeight: '600' },
  groupPill: {
    borderWidth: 1,
    paddingHorizontal: 5, paddingVertical: 1,
    borderRadius: Radius.full,
  },
  groupPillText: { color: Colors.brand.primary, fontSize: 9 },
  alertTriggeredBadge: {
    backgroundColor: Colors.brand.primary,
    paddingHorizontal: 5, paddingVertical: 1,
    borderRadius: Radius.full,
  },
  alertTriggeredText: { color: Colors.bg.primary, fontSize: 9, fontWeight: '700' },
  stockMeta: { flexDirection: 'row', alignItems: 'center', gap: Spacing.md },
  stockCode: { color: Colors.text.muted, fontSize: 11 },
  stockPrice: { fontSize: 12, fontVariant: ['tabular-nums'] },
  alertSummary: { color: Colors.brand.primary, fontSize: 10, marginTop: 2 },
  noteText: { color: Colors.text.muted, fontSize: 10, marginTop: 2 },
  actionCol: { paddingRight: Spacing.sm, gap: 2 },
  actionBtn: { padding: 5 },
  actionIcon: { fontSize: 14 },
  empty: { padding: 40, alignItems: 'center', gap: 12 },
  emptyText: { color: Colors.text.muted, fontSize: 15 },
  emptyBtn: {
    backgroundColor: Colors.brand.primary,
    paddingHorizontal: 24, paddingVertical: 10,
    borderRadius: Radius.full,
  },
  emptyBtnText: { color: Colors.bg.primary, fontWeight: '700', fontSize: 14 },
  modalBackdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.55)',
  },
  modalCard: {
    position: 'absolute',
    bottom: 0, left: 0, right: 0,
    backgroundColor: Colors.bg.secondary,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: Spacing.xl,
    paddingBottom: 36,
  },
  modalTitle: { color: Colors.text.primary, fontSize: 16, fontWeight: '700', marginBottom: Spacing.lg, textAlign: 'center' },
  modalOption: {
    paddingVertical: Spacing.md,
    borderBottomWidth: 0.5,
    borderBottomColor: Colors.bg.border,
  },
  modalOptionText: { color: Colors.text.primary, fontSize: 15 },
  modalDivider: { height: Spacing.md },
  modalInput: {
    backgroundColor: Colors.bg.elevated,
    color: Colors.text.primary,
    borderRadius: Radius.md,
    paddingHorizontal: Spacing.md,
    paddingVertical: 11,
    fontSize: 14,
    marginBottom: Spacing.sm,
  },
  noteInput: { height: 80, textAlignVertical: 'top', paddingTop: 10 },
  noteCount: { color: Colors.text.muted, fontSize: 10, textAlign: 'right', marginBottom: Spacing.md },
  modalConfirmBtn: {
    backgroundColor: Colors.brand.primary,
    paddingVertical: 13,
    borderRadius: Radius.md,
    alignItems: 'center',
    marginTop: Spacing.sm,
  },
  modalConfirmText: { color: Colors.bg.primary, fontSize: 15, fontWeight: '700' },
});
