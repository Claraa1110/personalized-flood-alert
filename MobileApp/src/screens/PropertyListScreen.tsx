import { useState, useCallback } from 'react';
import {
  View, TouchableOpacity, Text, StyleSheet,
  ActivityIndicator, FlatList, RefreshControl,
  Modal, TextInput, KeyboardAvoidingView, Platform, Alert, ScrollView,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import AddPropertyScreen from './AddPropertyScreen';
import TypeSelector from '../components/TypeSelector';
import StarSelector from '../components/StarSelector';
import LocationTabPicker from '../components/LocationTabPicker';
import { apiFetch } from '../lib/api';
import { PropertyType, TYPE_ICONS, getAdvice } from '../lib/advice';
import {
  PropertyWithRisk,
  getCachedProperties, isPropertyCacheFresh,
  fetchPropertiesWithRisk, invalidatePropertyCache,
} from '../lib/propertyCache';

// ─── Types ────────────────────────────────────────────────────────────────────

type GroupKey = 'house' | 'car' | 'shop' | 'other';

interface GroupData {
  key: GroupKey;
  label: string;
  icon: string;
  items: PropertyWithRisk[];
  alertCount: number;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const TYPE_TO_GROUP: Record<string, GroupKey> = {
  house: 'house', car: 'car', shop: 'shop',
  warehouse: 'other', farm: 'other', custom: 'other', other: 'other',
};

const GROUP_INFO: Record<GroupKey, { label: string; icon: string }> = {
  house: { label: '住家', icon: 'home' },
  car:   { label: '車輛', icon: 'car' },
  shop:  { label: '店面', icon: 'storefront' },
  other: { label: '其他', icon: 'cube' },
};

const GROUP_ORDER: GroupKey[] = ['house', 'car', 'shop', 'other'];

// null = 正常；設定值可強制所有卡片顯示對應等級（測試用）
const DEBUG_LEVEL: 'safe' | 'level2' | 'level1' | null = null;

// ─── Helpers ──────────────────────────────────────────────────────────────────

function getRiskDot(level: string | null) {
  if (!level || level === 'safe') return { color: '#27AE60', label: '安全' };
  if (level === 'level2') return { color: '#F5A623', label: '注意' };
  return { color: '#C00000', label: '警戒' };
}

function buildGroups(properties: PropertyWithRisk[]): GroupData[] {
  const map: Partial<Record<GroupKey, PropertyWithRisk[]>> = {};
  for (const p of properties) {
    const g = TYPE_TO_GROUP[p.type ?? 'house'] ?? 'other';
    if (!map[g]) map[g] = [];
    map[g]!.push(p);
  }
  const groups: GroupData[] = GROUP_ORDER
    .filter(k => !!map[k])
    .map(k => ({
      key: k,
      ...GROUP_INFO[k],
      items: map[k]!,
      alertCount: map[k]!.filter(p => {
        const lv = DEBUG_LEVEL ?? p.level;
        return lv === 'level1' || lv === 'level2';
      }).length,
    }));

  groups.sort((a, b) => {
    if (a.alertCount > 0 && b.alertCount === 0) return -1;
    if (a.alertCount === 0 && b.alertCount > 0) return 1;
    return GROUP_ORDER.indexOf(a.key) - GROUP_ORDER.indexOf(b.key);
  });
  return groups;
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function PropertyListScreen() {
  const [properties, setProperties] = useState<PropertyWithRisk[]>(() => getCachedProperties());
  const [listLoading, setListLoading] = useState(() => getCachedProperties().length === 0);
  const [isSyncing, setIsSyncing] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [listError, setListError] = useState<string | null>(null);
  const [selectedGroup, setSelectedGroup] = useState<GroupKey | null>(null);

  // Add modal
  const [addVisible, setAddVisible] = useState(false);

  // Edit modal
  const [editingProperty, setEditingProperty] = useState<PropertyWithRisk | null>(null);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editName, setEditName] = useState('');
  const [editType, setEditType] = useState<PropertyType>('house');
  const [editCustomTypeName, setEditCustomTypeName] = useState('');
  const [editLat, setEditLat] = useState(0);
  const [editLng, setEditLng] = useState(0);
  const [editAddress, setEditAddress] = useState('');
  const [editPriorityStars, setEditPriorityStars] = useState(3);
  const [editSubmitting, setEditSubmitting] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  // ── Data Fetching ────────────────────────────────────────────────────────────

  const fetchData = async (force = false) => {
    if (!force && isPropertyCacheFresh()) {
      const cached = getCachedProperties();
      if (cached.length > 0) setProperties(cached);
      return;
    }
    const hasCache = getCachedProperties().length > 0;
    if (hasCache) { setIsSyncing(true); } else { setListLoading(true); }
    setListError(null);
    try {
      const data = await fetchPropertiesWithRisk(force);
      setProperties(data);
    } catch (e: any) {
      if (!hasCache) setListError(e.message ?? '無法載入財產');
    } finally {
      setListLoading(false);
      setIsSyncing(false);
      setRefreshing(false);
    }
  };

  useFocusEffect(useCallback(() => { fetchData(); }, []));

  const onRefresh = () => { setRefreshing(true); fetchData(true); };

  const groups = buildGroups(properties);

  // ── Edit Handlers ────────────────────────────────────────────────────────────

  const openEdit = (p: PropertyWithRisk) => {
    setEditingProperty(p);
    setEditName(p.name);
    const rawType = p.type as string;
    const resolvedType = (rawType === 'other' ? 'warehouse' : rawType) as PropertyType ?? 'house';
    setEditType(resolvedType);
    setEditCustomTypeName(p.custom_type_name ?? '');
    setEditAddress(p.address ?? '');
    setEditLat(p.latitude);
    setEditLng(p.longitude);
    setEditPriorityStars(p.priority_stars ?? 3);
    setEditError(null);
    setEditModalVisible(true);
  };

  const closeEdit = () => { setEditModalVisible(false); setEditingProperty(null); };

  const saveEdit = async () => {
    if (!editName.trim()) { setEditError('請輸入財產名稱'); return; }
    if (!editingProperty) return;
    setEditSubmitting(true);
    setEditError(null);
    try {
      const resp = await apiFetch(`/api/properties/${editingProperty.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: editName.trim(),
          address: editAddress.trim() || null,
          latitude: editLat, longitude: editLng,
          type: editType,
          custom_type_name: editType === 'custom' ? editCustomTypeName.trim() || null : null,
          priority_stars: editPriorityStars,
        }),
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error((err as any).detail ?? `HTTP ${resp.status}`);
      }
      closeEdit();
      invalidatePropertyCache();
      fetchData(true);
    } catch (e: any) {
      setEditError(e.message ?? '儲存失敗');
    } finally {
      setEditSubmitting(false);
    }
  };

  const confirmDelete = () => {
    Alert.alert('刪除財產', `確定要刪除「${editingProperty?.name}」嗎？此操作無法復原。`, [
      { text: '取消', style: 'cancel' },
      { text: '刪除', style: 'destructive', onPress: deleteProperty },
    ]);
  };

  const deleteProperty = async () => {
    if (!editingProperty) return;
    setEditSubmitting(true);
    try {
      const resp = await apiFetch(`/api/properties/${editingProperty.id}`, { method: 'DELETE' });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      closeEdit();
      // 如果刪完後該類型沒有財產了，返回第一層
      const remaining = properties.filter(p => p.id !== editingProperty.id);
      const stillInGroup = remaining.some(p => (TYPE_TO_GROUP[p.type ?? 'house'] ?? 'other') === selectedGroup);
      if (!stillInGroup) setSelectedGroup(null);
      invalidatePropertyCache();
      fetchData(true);
    } catch (e: any) {
      setEditError(e.message ?? '刪除失敗');
    } finally {
      setEditSubmitting(false);
    }
  };

  // ── Shared modals ─────────────────────────────────────────────────────────────

  const addModal = (
    <Modal visible={addVisible} animationType="slide" onRequestClose={() => setAddVisible(false)}>
      <AddPropertyScreen
        onComplete={() => { setAddVisible(false); invalidatePropertyCache(); fetchData(true); }}
        onCancel={() => setAddVisible(false)}
      />
    </Modal>
  );

  const editModal = (
    <Modal visible={editModalVisible} transparent animationType="slide" onRequestClose={closeEdit}>
      <KeyboardAvoidingView style={styles.modalOverlay} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
        <View style={styles.modalBox}>
          <View style={styles.editHeader}>
            <Text style={styles.modalTitle}>編輯財產</Text>
            <TouchableOpacity onPress={closeEdit}>
              <Ionicons name="close" size={22} color="#888" />
            </TouchableOpacity>
          </View>
          <ScrollView showsVerticalScrollIndicator={false} keyboardShouldPersistTaps="handled">
            <Text style={styles.inputLabel}>財產名稱</Text>
            <TextInput style={styles.input} value={editName} onChangeText={setEditName} autoFocus />

            <Text style={styles.inputLabel}>財產類型</Text>
            <TypeSelector value={editType} onChange={setEditType}
              customTypeName={editCustomTypeName} onCustomTypeNameChange={setEditCustomTypeName} />

            <Text style={styles.inputLabel}>重要程度</Text>
            <StarSelector value={editPriorityStars} onChange={setEditPriorityStars} />

            <Text style={styles.inputLabel}>財產位置</Text>
            <LocationTabPicker
              initialLat={editLat} initialLng={editLng} initialAddress={editAddress}
              onLocationChange={(la, ln, addr) => { setEditLat(la); setEditLng(ln); setEditAddress(addr ?? ''); }}
            />

            {editError ? (
              <View style={styles.formErrorBox}>
                <Ionicons name="alert-circle-outline" size={14} color="#C00000" />
                <Text style={styles.formErrorText}>{editError}</Text>
              </View>
            ) : null}

            <View style={styles.modalBtns}>
              <TouchableOpacity style={styles.deleteBtn} onPress={confirmDelete} disabled={editSubmitting}>
                <Ionicons name="trash-outline" size={18} color="#C00000" />
                <Text style={styles.deleteBtnText}>刪除</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.confirmBtn} onPress={saveEdit} disabled={editSubmitting}>
                {editSubmitting
                  ? <ActivityIndicator color="#fff" size="small" />
                  : <><Ionicons name="checkmark" size={18} color="#fff" /><Text style={styles.confirmBtnText}>儲存</Text></>}
              </TouchableOpacity>
            </View>
          </ScrollView>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );

  const fab = (
    <TouchableOpacity style={styles.fab} onPress={() => setAddVisible(true)} activeOpacity={0.85}>
      <Ionicons name="add" size={30} color="#fff" />
    </TouchableOpacity>
  );

  // ── Full-screen states ────────────────────────────────────────────────────────

  if (listLoading && properties.length === 0) {
    return (
      <View style={[styles.container, styles.center]}>
        <ActivityIndicator size="large" color="#2E75B6" />
        <Text style={styles.loadingText}>載入中...</Text>
      </View>
    );
  }

  if (listError && properties.length === 0) {
    return (
      <View style={[styles.container, styles.center]}>
        <Ionicons name="cloud-offline-outline" size={52} color="#ccc" />
        <Text style={styles.errorText}>{listError}</Text>
        <Text style={styles.errorSub}>下拉畫面或點擊重試</Text>
        <TouchableOpacity style={styles.retryBtn} onPress={() => fetchData(true)}>
          <Text style={styles.retryBtnText}>重試</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (!listLoading && properties.length === 0) {
    return (
      <View style={[styles.container, styles.center]}>
        <Ionicons name="home-outline" size={60} color="#ddd" />
        <Text style={styles.emptyText}>還沒有任何財產</Text>
        <Text style={styles.emptySubtext}>新增家、車或店面，讓水先知幫你盯著</Text>
        <TouchableOpacity style={styles.emptyAddBtn} onPress={() => setAddVisible(true)} activeOpacity={0.85}>
          <Ionicons name="add-circle-outline" size={20} color="#fff" />
          <Text style={styles.emptyAddBtnText}>新增第一個財產</Text>
        </TouchableOpacity>
        {addModal}
      </View>
    );
  }

  // ── Layer 2：某類型的財產清單 ────────────────────────────────────────────────

  if (selectedGroup !== null) {
    const groupData = groups.find(g => g.key === selectedGroup);
    const items = groupData?.items ?? [];
    const info = GROUP_INFO[selectedGroup];

    const renderRow = ({ item }: { item: PropertyWithRisk }) => {
      const level = DEBUG_LEVEL ?? item.level;
      const risk = getRiskDot(level);
      const advice = getAdvice(level, item.type ?? 'house');
      return (
        <TouchableOpacity style={styles.propertyRow} onPress={() => openEdit(item)} activeOpacity={0.82}>
          <View style={[styles.riskDot, { backgroundColor: risk.color }]} />
          <View style={styles.propertyRowBody}>
            <Text style={styles.propertyRowName} numberOfLines={1}>{item.name}</Text>
            {item.district_name
              ? <Text style={styles.propertyRowDistrict}>{item.district_name}</Text>
              : null}
            {advice
              ? <Text style={[styles.propertyRowAdvice, { color: advice.textColor }]} numberOfLines={1}>
                  {advice.icon} {advice.text}
                </Text>
              : null}
          </View>
          {item.rainfall['1h'] > 0
            ? <View style={styles.rainfallChip}>
                <Ionicons name="rainy-outline" size={11} color="#2E75B6" />
                <Text style={styles.rainfallChipText}>{item.rainfall['1h']}mm</Text>
              </View>
            : null}
          <Ionicons name="chevron-forward" size={16} color="#ccc" />
        </TouchableOpacity>
      );
    };

    return (
      <View style={styles.container}>
        {/* 子頁頭 */}
        <View style={styles.subHeader}>
          <TouchableOpacity style={styles.backBtn} onPress={() => setSelectedGroup(null)} activeOpacity={0.7}>
            <Ionicons name="chevron-back" size={20} color="#2E75B6" />
            <Text style={styles.backBtnText}>分類</Text>
          </TouchableOpacity>
          <View style={styles.subHeaderCenter}>
            <Ionicons name={info.icon as any} size={16} color="#2E75B6" />
            <Text style={styles.subHeaderTitle}>{info.label}</Text>
          </View>
          <View style={{ width: 64 }} />
        </View>

        <FlatList
          data={items}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.propertyListContent}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
          renderItem={renderRow}
          ItemSeparatorComponent={() => <View style={styles.separator} />}
        />

        {fab}
        {addModal}
        {editModal}
      </View>
    );
  }

  // ── Layer 1：類型總覽 ────────────────────────────────────────────────────────

  const renderGroupCard = ({ item: g }: { item: GroupData }) => {
    const hasAlert = g.alertCount > 0;
    return (
      <TouchableOpacity
        style={[styles.groupCard, hasAlert && styles.groupCardAlert]}
        onPress={() => setSelectedGroup(g.key)}
        activeOpacity={0.82}
      >
        <View style={[styles.groupIconWrap, hasAlert && styles.groupIconWrapAlert]}>
          <Ionicons name={g.icon as any} size={22} color={hasAlert ? '#C00000' : '#2E75B6'} />
        </View>

        <View style={styles.groupBody}>
          <Text style={[styles.groupLabel, hasAlert && styles.groupLabelAlert]}>{g.label}</Text>
          <Text style={styles.groupCount}>{g.items.length} 個財產</Text>
        </View>

        {hasAlert ? (
          <View style={styles.alertBadge}>
            <Ionicons name="warning" size={11} color="#fff" />
            <Text style={styles.alertBadgeText}>{g.alertCount}</Text>
          </View>
        ) : null}

        <Ionicons name="chevron-forward" size={18} color="#ccc" />
      </TouchableOpacity>
    );
  };

  return (
    <View style={styles.container}>
      {/* 統計列 */}
      <View style={styles.statsBar}>
        <Text style={styles.statsText}>共 {properties.length} 個財產</Text>
        {isSyncing && <ActivityIndicator size="small" color="#2E75B6" style={styles.syncIndicator} />}
      </View>

      <FlatList
        data={groups}
        keyExtractor={(g) => g.key}
        contentContainerStyle={styles.groupListContent}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        renderItem={renderGroupCard}
      />

      {fab}
      {addModal}
      {editModal}
    </View>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F0F4F8' },

  // ── Full-screen states ──
  center: { justifyContent: 'center', alignItems: 'center', gap: 10, padding: 32 },
  loadingText: { color: '#aaa', fontSize: 14 },
  errorText: { fontSize: 16, fontWeight: '600', color: '#C00000', textAlign: 'center', marginTop: 8 },
  errorSub: { fontSize: 13, color: '#aaa', textAlign: 'center' },
  retryBtn: { backgroundColor: '#2E75B6', paddingHorizontal: 28, paddingVertical: 10, borderRadius: 20, marginTop: 4 },
  retryBtnText: { color: '#fff', fontWeight: '600' },
  emptyText: { fontSize: 18, fontWeight: '700', color: '#aaa', marginTop: 12 },
  emptySubtext: { fontSize: 13, color: '#bbb', textAlign: 'center' },
  emptyAddBtn: {
    flexDirection: 'row', alignItems: 'center', gap: 8,
    backgroundColor: '#2E75B6', paddingVertical: 13, paddingHorizontal: 24,
    borderRadius: 14, marginTop: 12,
  },
  emptyAddBtnText: { fontSize: 15, fontWeight: '700', color: '#fff' },

  // ── Layer 1 ──
  statsBar: {
    flexDirection: 'row', alignItems: 'center',
    paddingHorizontal: 20, paddingVertical: 12,
    backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: '#EAEAEA',
  },
  statsText: { fontSize: 13, color: '#888', flex: 1 },
  syncIndicator: { marginLeft: 8 },
  groupListContent: { padding: 16, gap: 12, paddingBottom: 88 },

  groupCard: {
    flexDirection: 'row', alignItems: 'center', gap: 14,
    backgroundColor: '#fff', borderRadius: 16, padding: 18,
    shadowColor: '#000', shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.07, shadowRadius: 6, elevation: 3,
  },
  groupCardAlert: {
    borderWidth: 1.5, borderColor: '#C00000',
    shadowColor: '#C00000', shadowOpacity: 0.15,
  },
  groupIconWrap: {
    width: 44, height: 44, borderRadius: 12,
    backgroundColor: '#EBF3FB', alignItems: 'center', justifyContent: 'center',
  },
  groupIconWrapAlert: { backgroundColor: '#FDECEA' },
  groupBody: { flex: 1, gap: 3 },
  groupLabel: { fontSize: 16, fontWeight: '700', color: '#1A1A2E' },
  groupLabelAlert: { color: '#C00000' },
  groupCount: { fontSize: 12, color: '#888' },
  alertBadge: {
    flexDirection: 'row', alignItems: 'center', gap: 3,
    backgroundColor: '#C00000', borderRadius: 10,
    paddingHorizontal: 7, paddingVertical: 3,
  },
  alertBadgeText: { fontSize: 11, color: '#fff', fontWeight: '700' },

  // ── Layer 2 ──
  subHeader: {
    flexDirection: 'row', alignItems: 'center',
    backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: '#EAEAEA',
    paddingHorizontal: 8, paddingVertical: 12,
  },
  backBtn: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 8, gap: 2, minWidth: 64 },
  backBtnText: { fontSize: 15, color: '#2E75B6', fontWeight: '500' },
  subHeaderCenter: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6 },
  subHeaderTitle: { fontSize: 16, fontWeight: '700', color: '#1A1A2E' },

  propertyListContent: { paddingBottom: 88 },
  propertyRow: {
    flexDirection: 'row', alignItems: 'center', gap: 12,
    backgroundColor: '#fff', paddingHorizontal: 18, paddingVertical: 14,
  },
  riskDot: { width: 11, height: 11, borderRadius: 6, flexShrink: 0 },
  propertyRowBody: { flex: 1, gap: 2 },
  propertyRowName: { fontSize: 15, fontWeight: '600', color: '#1A1A2E' },
  propertyRowDistrict: { fontSize: 12, color: '#888' },
  propertyRowAdvice: { fontSize: 12, marginTop: 2 },
  rainfallChip: {
    flexDirection: 'row', alignItems: 'center', gap: 3,
    backgroundColor: '#EBF3FB', paddingHorizontal: 7, paddingVertical: 3, borderRadius: 8,
  },
  rainfallChipText: { fontSize: 11, color: '#2E75B6', fontWeight: '600' },
  separator: { height: 1, backgroundColor: '#F0F4F8', marginLeft: 41 },

  // ── FAB ──
  fab: {
    position: 'absolute', bottom: 28, right: 24,
    width: 58, height: 58, borderRadius: 29, backgroundColor: '#2E75B6',
    alignItems: 'center', justifyContent: 'center',
    shadowColor: '#2E75B6', shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.4, shadowRadius: 8, elevation: 8,
  },

  // ── Edit Modal ──
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', paddingHorizontal: 24 },
  modalBox: {
    backgroundColor: '#fff', borderRadius: 24,
    padding: 24, paddingBottom: 32, maxHeight: '85%',
    shadowColor: '#000', shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.15, shadowRadius: 16, elevation: 12,
  },
  modalTitle: { fontSize: 20, fontWeight: '700', color: '#1A1A2E' },
  editHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 },
  inputLabel: { fontSize: 13, color: '#555', fontWeight: '600', marginBottom: 8, marginTop: 16 },
  input: {
    borderWidth: 1.5, borderColor: '#E0E0E0', borderRadius: 10,
    paddingHorizontal: 14, paddingVertical: 11, fontSize: 15, color: '#222', backgroundColor: '#FAFAFA',
  },
  formErrorBox: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 12, backgroundColor: '#FFF0F0', padding: 10, borderRadius: 8 },
  formErrorText: { color: '#C00000', fontSize: 13, flex: 1 },
  modalBtns: { flexDirection: 'row', gap: 12, marginTop: 24 },
  confirmBtn: { flex: 2, paddingVertical: 13, borderRadius: 12, backgroundColor: '#2E75B6', alignItems: 'center', flexDirection: 'row', justifyContent: 'center', gap: 6 },
  confirmBtnText: { fontSize: 15, color: '#fff', fontWeight: '700' },
  deleteBtn: { flex: 1, paddingVertical: 13, borderRadius: 12, backgroundColor: '#FFF0F0', alignItems: 'center', flexDirection: 'row', justifyContent: 'center', gap: 6, borderWidth: 1.5, borderColor: '#FFCCCC' },
  deleteBtnText: { fontSize: 15, color: '#C00000', fontWeight: '600' },
});
