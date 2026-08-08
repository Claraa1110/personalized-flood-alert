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
import LocationTabPicker from '../components/LocationTabPicker';
import { apiFetch } from '../lib/api';
import { PropertyType, TYPE_ICONS, getAdvice } from '../lib/advice';
import {
  PropertyWithRisk,
  getCachedProperties, isPropertyCacheFresh,
  fetchPropertiesWithRisk, invalidatePropertyCache,
} from '../lib/propertyCache';

// ─── Types ────────────────────────────────────────────────────────────────────

interface ActiveAlert {
  level: 'level1' | 'level2';
  scale: string;
  actualMm: string;
  thresholdMm: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const MSG_RE = /【.+?】達(?:一級警戒|二級預警)\s+(\w+)\s+雨量\s+([\d.]+)mm（已達(?:警戒|預警)值\s+([\d.]+)mm）/;

// ─── Helpers ──────────────────────────────────────────────────────────────────

// null = 正常運行；設定 'level2' 或 'level1' 可強制所有卡片顯示對應等級（測試用）
const DEBUG_LEVEL: 'safe' | 'level2' | 'level1' | null = null;

function parseAlert(message: string, level: string): ActiveAlert | null {
  const m = message.match(MSG_RE);
  if (!m) return null;
  return {
    level: level === 'level1' ? 'level1' : 'level2',
    scale: m[1],
    actualMm: m[2],
    thresholdMm: m[3],
  };
}

function getRiskDot(level: 'safe' | 'level2' | 'level1' | null) {
  if (!level || level === 'safe') return { color: '#27AE60', label: '安全' };
  if (level === 'level2') return { color: '#F1C40F', label: '注意' };
  return { color: '#C00000', label: '警戒' };
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function PropertyListScreen() {
  const [properties, setProperties] = useState<PropertyWithRisk[]>(() => getCachedProperties());
  const [listLoading, setListLoading] = useState(() => getCachedProperties().length === 0);
  const [refreshing, setRefreshing] = useState(false);
  const [listError, setListError] = useState<string | null>(null);
  const [activeAlerts, setActiveAlerts] = useState<Record<string, ActiveAlert>>({});

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
  const [editSubmitting, setEditSubmitting] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  // ── Data Fetching ────────────────────────────────────────────────────────────

  const fetchData = async (force = false) => {
    // 快取命中：立即顯示快取資料，不顯示 spinner（module-level 函式規避 stale closure）
    if (!force && isPropertyCacheFresh()) {
      const cached = getCachedProperties();
      if (cached.length > 0) setProperties(cached);
      return;
    }

    // 完全無資料（第一次）才顯示全畫面 spinner
    if (getCachedProperties().length === 0) setListLoading(true);
    setListError(null);

    try {
      const [riskResult, alertResp] = await Promise.allSettled([
        fetchPropertiesWithRisk(force),
        apiFetch('/api/alerts'),
      ]);

      if (riskResult.status === 'fulfilled') {
        setProperties(riskResult.value);
      } else {
        throw new Error('無法載入財產');
      }

      if (alertResp.status === 'fulfilled' && alertResp.value.ok) {
        const alertData = await alertResp.value.json();
        const list: { property_id: string; message: string; created_at: string; level: string }[] =
          alertData.alerts ?? alertData;
        const alertMap: Record<string, ActiveAlert> = {};
        const sixHoursAgo = Date.now() - 6 * 60 * 60 * 1000;
        for (const a of list) {
          if (a.level !== 'level1' && a.level !== 'level2') continue;
          if (new Date(a.created_at + 'Z').getTime() < sixHoursAgo) continue;
          if (alertMap[a.property_id]) continue;
          const parsed = parseAlert(a.message, a.level);
          if (parsed) alertMap[a.property_id] = parsed;
        }
        setActiveAlerts(alertMap);
      }
    } catch (e: any) {
      setListError(e.message ?? '無法載入財產');
    } finally {
      setListLoading(false);
      setRefreshing(false);
    }
  };

  useFocusEffect(useCallback(() => { fetchData(); }, []));

  const onRefresh = () => { setRefreshing(true); fetchData(true); };

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
    setEditError(null);
    setEditModalVisible(true);
  };

  const closeEdit = () => {
    setEditModalVisible(false);
    setEditingProperty(null);
  };

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
          latitude: editLat,
          longitude: editLng,
          type: editType,
          custom_type_name: editType === 'custom' ? editCustomTypeName.trim() || null : null,
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
    Alert.alert(
      '刪除財產',
      `確定要刪除「${editingProperty?.name}」嗎？此操作無法復原。`,
      [
        { text: '取消', style: 'cancel' },
        { text: '刪除', style: 'destructive', onPress: deleteProperty },
      ]
    );
  };

  const deleteProperty = async () => {
    if (!editingProperty) return;
    setEditSubmitting(true);
    try {
      const resp = await apiFetch(`/api/properties/${editingProperty.id}`, { method: 'DELETE' });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      closeEdit();
      invalidatePropertyCache();
      fetchData(true);
    } catch (e: any) {
      setEditError(e.message ?? '刪除失敗');
    } finally {
      setEditSubmitting(false);
    }
  };

  // ── Render Item ───────────────────────────────────────────────────────────────

  const renderProperty = ({ item }: { item: PropertyWithRisk }) => {
    const typeKey = item.type ?? 'house';
    const iconName = TYPE_ICONS[typeKey] ?? 'cube';
    const level = DEBUG_LEVEL ?? item.level;
    const alert = activeAlerts[item.id];
    const hasAlert = !!alert && level !== 'safe';
    const risk = getRiskDot(level);
    const advice = getAdvice(level, typeKey);

    return (
      <TouchableOpacity
        style={hasAlert ? [styles.card, styles.cardAlert] : styles.card}
        onPress={() => openEdit(item)}
        activeOpacity={0.85}
      >
        {hasAlert && (
          <View style={styles.alertBanner}>
            <Ionicons name="warning" size={14} color="#fff" />
            <Text style={styles.alertBannerText}>
              {alert.level === 'level1' ? '警戒' : '注意'}
            </Text>
          </View>
        )}
        <View style={styles.cardContent}>
          <View style={styles.cardHeader}>
            <View style={hasAlert ? [styles.cardIconWrap, styles.cardIconWrapAlert] : styles.cardIconWrap}>
              <Ionicons name={iconName as any} size={18} color={hasAlert ? '#C00000' : '#2E75B6'} />
            </View>

            <View style={styles.cardTitleWrap}>
              <Text style={hasAlert ? [styles.cardName, styles.cardNameAlert] : styles.cardName}>
                {item.name}
              </Text>
              {item.district_name ? (
                <Text style={styles.cardDistrict}>{item.district_name}</Text>
              ) : null}
            </View>

            <View style={styles.riskDotWrap}>
              <View style={[styles.riskDot, { backgroundColor: risk.color }]} />
              <Text style={[styles.riskDotLabel, { color: risk.color }]}>{risk.label}</Text>
            </View>

            <Ionicons name="chevron-forward" size={16} color="#ccc" />
          </View>

          <View style={styles.addressRow}>
            {item.rainfall['1h'] > 0 ? (
              <View style={styles.rainfallChip}>
                <Ionicons name="rainy-outline" size={12} color="#2E75B6" />
                <Text style={styles.rainfallChipText}>{item.rainfall['1h']} mm</Text>
              </View>
            ) : null}
          </View>

          {advice ? (
            <View style={[styles.adviceBox, { backgroundColor: advice.bg, borderColor: advice.border }]}>
              <Text style={styles.adviceIcon}>{advice.icon}</Text>
              <View style={{ flex: 1 }}>
                <Text style={styles.adviceLabel}>行動建議</Text>
                <Text style={[styles.adviceText, { color: advice.textColor }]}>{advice.text}</Text>
              </View>
            </View>
          ) : null}
        </View>
      </TouchableOpacity>
    );
  };

  // ── Main Render ───────────────────────────────────────────────────────────────

  return (
    <View style={styles.container}>
      {(!listLoading && !listError) ? (
        <View style={styles.statsBar}>
          <Text style={styles.statsText}>共 {properties.length} 個財產</Text>
        </View>
      ) : null}

      {(listLoading && properties.length === 0) ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color="#2E75B6" />
          <Text style={styles.loadingText}>載入中...</Text>
        </View>
      ) : listError ? (
        <View style={styles.center}>
          <Ionicons name="cloud-offline-outline" size={48} color="#ccc" />
          <Text style={styles.errorText}>{listError}</Text>
          <TouchableOpacity style={styles.retryBtn} onPress={() => fetchData(true)}>
            <Text style={styles.retryBtnText}>重試</Text>
          </TouchableOpacity>
        </View>
      ) : properties.length === 0 ? (
        <View style={styles.center}>
          <Ionicons name="home-outline" size={56} color="#ddd" />
          <Text style={styles.emptyText}>尚未新增任何財產</Text>
          <Text style={styles.emptySubtext}>點右下角「＋」開始新增</Text>
        </View>
      ) : (
        <FlatList
          data={properties}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.listContent}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
          renderItem={renderProperty}
        />
      )}

      <TouchableOpacity style={styles.fab} onPress={() => setAddVisible(true)} activeOpacity={0.85}>
        <Ionicons name="add" size={30} color="#fff" />
      </TouchableOpacity>

      {/* ── AddPropertyScreen (full-screen modal) ── */}
      <Modal visible={addVisible} animationType="slide" onRequestClose={() => setAddVisible(false)}>
        <AddPropertyScreen
          onComplete={() => {
            setAddVisible(false);
            invalidatePropertyCache();
            fetchData(true);
          }}
          onCancel={() => setAddVisible(false)}
        />
      </Modal>

      {/* ── Edit Modal ── */}
      <Modal
        visible={editModalVisible}
        transparent
        animationType="slide"
        onRequestClose={closeEdit}
      >
        <KeyboardAvoidingView
          style={styles.modalOverlay}
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        >
          <View style={styles.modalBox}>
            <View style={styles.editHeader}>
              <Text style={styles.modalTitle}>編輯財產</Text>
              <TouchableOpacity onPress={closeEdit}>
                <Ionicons name="close" size={22} color="#888" />
              </TouchableOpacity>
            </View>

            <ScrollView
              showsVerticalScrollIndicator={false}
              keyboardShouldPersistTaps="handled"
            >
              <Text style={styles.inputLabel}>財產名稱</Text>
              <TextInput
                style={styles.input}
                value={editName}
                onChangeText={setEditName}
                autoFocus
              />

              <Text style={styles.inputLabel}>財產類型</Text>
              <TypeSelector
                value={editType}
                onChange={setEditType}
                customTypeName={editCustomTypeName}
                onCustomTypeNameChange={setEditCustomTypeName}
              />

              <Text style={styles.inputLabel}>財產位置</Text>
              <LocationTabPicker
                initialLat={editLat}
                initialLng={editLng}
                initialAddress={editAddress}
                onLocationChange={(la, ln, addr) => {
                  setEditLat(la);
                  setEditLng(ln);
                  setEditAddress(addr ?? '');
                }}
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
                  {editSubmitting ? <ActivityIndicator color="#fff" size="small" /> : (
                    <>
                      <Ionicons name="checkmark" size={18} color="#fff" />
                      <Text style={styles.confirmBtnText}>儲存</Text>
                    </>
                  )}
                </TouchableOpacity>
              </View>
            </ScrollView>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </View>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F0F4F8' },
  statsBar: {
    paddingHorizontal: 20, paddingVertical: 10,
    backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: '#EAEAEA',
  },
  statsText: { fontSize: 13, color: '#888' },
  listContent: { padding: 16, gap: 12, paddingBottom: 88 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', gap: 10 },
  loadingText: { color: '#aaa', fontSize: 14 },
  emptyText: { fontSize: 17, fontWeight: '600', color: '#aaa', marginTop: 8 },
  emptySubtext: { fontSize: 13, color: '#bbb' },
  errorText: { color: '#C00000', fontSize: 15, marginTop: 8 },
  retryBtn: { backgroundColor: '#2E75B6', paddingHorizontal: 28, paddingVertical: 10, borderRadius: 20, marginTop: 4 },
  retryBtnText: { color: '#fff', fontWeight: '600' },

  card: {
    backgroundColor: '#fff', borderRadius: 16, overflow: 'hidden',
    shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.07, shadowRadius: 6, elevation: 3,
  },
  cardAlert: { borderWidth: 1.5, borderColor: '#C00000', shadowColor: '#C00000', shadowOpacity: 0.18 },
  alertBanner: {
    flexDirection: 'row', alignItems: 'center', gap: 6,
    backgroundColor: '#C00000', paddingHorizontal: 14, paddingVertical: 8,
  },
  alertBannerText: { color: '#fff', fontSize: 13, fontWeight: '600', flex: 1 },
  cardContent: { padding: 14 },
  cardHeader: { flexDirection: 'row', alignItems: 'flex-start', gap: 10, marginBottom: 6 },
  cardIconWrap: { width: 36, height: 36, borderRadius: 10, backgroundColor: '#EBF3FB', alignItems: 'center', justifyContent: 'center' },
  cardIconWrapAlert: { backgroundColor: '#FDECEA' },
  cardTitleWrap: { flex: 1 },
  cardName: { fontSize: 16, fontWeight: '700', color: '#1A1A2E' },
  cardNameAlert: { color: '#C00000' },
  cardDistrict: { fontSize: 12, color: '#888', marginTop: 1 },
  customTypeTag: { fontSize: 11, color: '#2E75B6', fontWeight: '600', marginTop: 2 },

  riskDotWrap: { alignItems: 'center', gap: 3, justifyContent: 'center' },
  riskDot: { width: 12, height: 12, borderRadius: 6 },
  riskDotLabel: { fontSize: 10, fontWeight: '700' },

  addressRow: { flexDirection: 'row', alignItems: 'center', gap: 4, flexWrap: 'wrap' },
  cardAddress: { fontSize: 12, color: '#999', flex: 1 },
  rainfallChip: {
    flexDirection: 'row', alignItems: 'center', gap: 3,
    backgroundColor: '#EBF3FB', paddingHorizontal: 7, paddingVertical: 2, borderRadius: 8, marginLeft: 'auto',
  },
  rainfallChipText: { fontSize: 11, color: '#2E75B6', fontWeight: '600' },

  adviceBox: {
    flexDirection: 'row', alignItems: 'flex-start', gap: 8,
    marginTop: 10, padding: 10, borderRadius: 10, borderWidth: 1,
  },
  adviceIcon: { fontSize: 16, lineHeight: 20 },
  adviceLabel: { fontSize: 10, fontWeight: '700', color: '#555', marginBottom: 2, textTransform: 'uppercase', letterSpacing: 0.4 },
  adviceText: { fontSize: 13, color: '#333', lineHeight: 18 },

  fab: {
    position: 'absolute', bottom: 28, right: 24,
    width: 58, height: 58, borderRadius: 29, backgroundColor: '#2E75B6',
    alignItems: 'center', justifyContent: 'center',
    shadowColor: '#2E75B6', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.4, shadowRadius: 8, elevation: 8,
  },

  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', paddingHorizontal: 24 },
  modalBox: {
    backgroundColor: '#fff', borderRadius: 24,
    padding: 24, paddingBottom: 32, maxHeight: '85%',
    shadowColor: '#000', shadowOffset: { width: 0, height: 8 }, shadowOpacity: 0.15, shadowRadius: 16, elevation: 12,
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
  cancelBtn: { flex: 1, paddingVertical: 13, borderRadius: 12, backgroundColor: '#F0F0F0', alignItems: 'center' },
  cancelBtnText: { fontSize: 15, color: '#666', fontWeight: '600' },
  confirmBtn: { flex: 2, paddingVertical: 13, borderRadius: 12, backgroundColor: '#2E75B6', alignItems: 'center', flexDirection: 'row', justifyContent: 'center', gap: 6 },
  confirmBtnText: { fontSize: 15, color: '#fff', fontWeight: '700' },
  deleteBtn: { flex: 1, paddingVertical: 13, borderRadius: 12, backgroundColor: '#FFF0F0', alignItems: 'center', flexDirection: 'row', justifyContent: 'center', gap: 6, borderWidth: 1.5, borderColor: '#FFCCCC' },
  deleteBtnText: { fontSize: 15, color: '#C00000', fontWeight: '600' },
});
