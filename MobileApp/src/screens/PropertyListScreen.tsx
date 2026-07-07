import { useState, useCallback } from 'react';
import {
  View, TouchableOpacity, Text, StyleSheet,
  ActivityIndicator, FlatList, RefreshControl,
  Modal, TextInput, KeyboardAvoidingView, Platform, Alert,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import MapView, { Region } from 'react-native-maps';
import AddPropertyScreen from './AddPropertyScreen';

// ─── Types ────────────────────────────────────────────────────────────────────

type PropertyType = 'house' | 'car' | 'warehouse' | 'other';

interface Property {
  id: string;
  name: string;
  type: PropertyType | null;
  address: string | null;
  latitude: number;
  longitude: number;
  district_name: string | null;
  flood_risk_level: number | null;
  rainfall_now_mm?: number | null;
}

interface Threshold {
  threshold_1h: number | null;
  threshold_3h: number | null;
  threshold_6h: number | null;
  source: string;
}

interface ActiveAlert {
  scale: string;
  actualMm: string;
  thresholdMm: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const MSG_RE = /【.+?】雨量超過警戒門檻\s+(\w+)（([\d.]+)mm\s*>=\s*([\d.]+)mm）/;

const TYPE_ICONS: Record<string, string> = {
  house:     'home',
  car:       'car',
  warehouse: 'business',
  other:     'cube',
};

const TAIWAN_CENTER: Region = {
  latitude: 23.5, longitude: 121.0,
  latitudeDelta: 5, longitudeDelta: 5,
};

const PIN_HEAD = 26;
const PIN_TAIL = 14;
const PIN_HEIGHT = PIN_HEAD + PIN_TAIL;

// ─── Helpers ──────────────────────────────────────────────────────────────────

// null = 正常運行；填入數字陣列可讓前幾張卡循環顯示對應風險 % 來測試
const DEBUG_PCT_CYCLE: (number | null)[] = [];

function parseAlert(message: string): ActiveAlert | null {
  const m = message.match(MSG_RE);
  if (!m) return null;
  return { scale: m[1], actualMm: m[2], thresholdMm: m[3] };
}

function calcRiskPct(rainfall: number | null | undefined, threshold1h: number | null | undefined, idx = 0): number | null {
  if (DEBUG_PCT_CYCLE.length > 0) return DEBUG_PCT_CYCLE[idx % DEBUG_PCT_CYCLE.length] ?? null;
  if (rainfall == null || !threshold1h) return null;
  return (rainfall / threshold1h) * 100;
}

function getRiskDot(pct: number | null) {
  if (pct == null) return { color: '#D0D0D0', label: '-' };
  if (pct >= 100) return { color: '#C00000', label: '高' };
  if (pct >= 80)  return { color: '#E67E22', label: '中高' };
  if (pct >= 50)  return { color: '#F1C40F', label: '中' };
  return { color: '#27AE60', label: '低' };
}

// 行動建議對照表（等級 × 財產類型）
const ADVICE_YELLOW = '留意天氣變化，確認排水孔暢通';
const ADVICE: Record<'orange' | 'red', Record<string, string>> = {
  orange: {
    house:     '貴重物品、家電移至高處，確認一樓門窗防水',
    car:       '盡快將車輛移往高處停放',
    warehouse: '墊高庫存，確認電源總開關位置',
    other:     '重要物品移至高處',
  },
  red: {
    house:     '緊急：一樓人員注意安全，切勿進入地下室',
    car:       '緊急：立即移車，遠離低窪停車區',
    warehouse: '緊急：關閉電源總開關，人員撤離',
    other:     '緊急：遠離淹水區域，注意人身安全',
  },
};

function getAdvice(pct: number | null, type: string): { text: string; bg: string; border: string; icon: string } | null {
  if (pct == null || pct < 50) return null;
  if (pct >= 100) return { text: ADVICE.red[type] ?? ADVICE.red.other, bg: '#FFF0F0', border: '#FFCCCC', icon: '⚠️' };
  if (pct >= 80)  return { text: ADVICE.orange[type] ?? ADVICE.orange.other, bg: '#FFF5EC', border: '#FFDDB8', icon: '⚠️' };
  return { text: ADVICE_YELLOW, bg: '#FFFBEA', border: '#FFE57F', icon: '💡' };
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function PropertyListScreen() {
  const base = process.env.EXPO_PUBLIC_API_URL;

  const [properties, setProperties] = useState<Property[]>([]);
  const [listLoading, setListLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [listError, setListError] = useState<string | null>(null);
  const [thresholds, setThresholds] = useState<Record<string, Threshold>>({});
  const [activeAlerts, setActiveAlerts] = useState<Record<string, ActiveAlert>>({});

  // Add modal
  const [addVisible, setAddVisible] = useState(false);

  // Edit flow
  const [editingProperty, setEditingProperty] = useState<Property | null>(null);
  const [editStep, setEditStep] = useState<0 | 1 | 2>(0);
  const [editLat, setEditLat] = useState(0);
  const [editLng, setEditLng] = useState(0);
  const [editName, setEditName] = useState('');
  const [editAddress, setEditAddress] = useState('');
  const [editSubmitting, setEditSubmitting] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  // ── Data Fetching ────────────────────────────────────────────────────────────

  const fetchProperties = async () => {
    setListError(null);
    try {
      const resp = await fetch(`${base}/api/properties`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data: Property[] = await resp.json();
      setProperties(data);

      const thresholdMap: Record<string, Threshold> = {};
      await Promise.all(
        data.map(async (p) => {
          try {
            const tr = await fetch(`${base}/api/threshold?lat=${p.latitude}&lng=${p.longitude}`);
            if (tr.ok) thresholdMap[p.id] = await tr.json();
          } catch (_) {}
        })
      );
      setThresholds(thresholdMap);

      try {
        const ar = await fetch(`${base}/api/alerts`);
        if (ar.ok) {
          const alertData = await ar.json();
          const list: { property_id: string; message: string; created_at: string; level: string }[] =
            alertData.alerts ?? alertData;
          const alertMap: Record<string, ActiveAlert> = {};
          const sixHoursAgo = Date.now() - 6 * 60 * 60 * 1000;
          for (const a of list) {
            if (a.level !== 'warning') continue;
            if (new Date(a.created_at).getTime() < sixHoursAgo) continue;
            if (alertMap[a.property_id]) continue;
            const parsed = parseAlert(a.message);
            if (parsed) alertMap[a.property_id] = parsed;
          }
          setActiveAlerts(alertMap);
        }
      } catch (_) {}
    } catch (e: any) {
      setListError(e.message ?? '無法載入財產');
    } finally {
      setListLoading(false);
      setRefreshing(false);
    }
  };

  useFocusEffect(useCallback(() => { fetchProperties(); }, []));

  const onRefresh = () => { setRefreshing(true); fetchProperties(); };

  // ── Edit Handlers ────────────────────────────────────────────────────────────

  const openEdit = (p: Property) => {
    setEditingProperty(p);
    setEditName(p.name);
    setEditAddress(p.address ?? '');
    setEditLat(p.latitude);
    setEditLng(p.longitude);
    setEditError(null);
    setEditStep(1);
  };

  const saveEdit = async () => {
    if (!editName.trim()) { setEditError('請輸入財產名稱'); return; }
    if (!editingProperty) return;
    setEditSubmitting(true);
    setEditError(null);
    try {
      const resp = await fetch(`${base}/api/properties/${editingProperty.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: editName.trim(),
          address: editAddress.trim() || null,
          latitude: editLat,
          longitude: editLng,
          type: editingProperty.type ?? 'house',
        }),
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error((err as any).detail ?? `HTTP ${resp.status}`);
      }
      setEditStep(0);
      setEditingProperty(null);
      fetchProperties();
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
      const resp = await fetch(`${base}/api/properties/${editingProperty.id}`, { method: 'DELETE' });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      setEditStep(0);
      setEditingProperty(null);
      fetchProperties();
    } catch (e: any) {
      setEditError(e.message ?? '刪除失敗');
    } finally {
      setEditSubmitting(false);
    }
  };

  // ── Render Item ───────────────────────────────────────────────────────────────

  const renderProperty = ({ item, index }: { item: Property; index: number }) => {
    const t = thresholds[item.id];
    const alert = activeAlerts[item.id];
    const hasAlert = !!alert;
    const typeKey = item.type ?? 'house';
    const iconName = TYPE_ICONS[typeKey] ?? 'cube';
    const pct = calcRiskPct(item.rainfall_now_mm, t?.threshold_1h, index);
    const risk = getRiskDot(pct);
    const advice = getAdvice(pct, typeKey);

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
              {alert.scale} 雨量 {alert.actualMm} mm　超過門檻 {alert.thresholdMm} mm
            </Text>
          </View>
        )}
        <View style={styles.cardContent}>
          <View style={styles.cardHeader}>
            {/* Type icon */}
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

            {/* Risk color dot */}
            <View style={styles.riskDotWrap}>
              <View style={[styles.riskDot, { backgroundColor: risk.color }]} />
              <Text style={[styles.riskDotLabel, { color: risk.color }]}>{risk.label}</Text>
            </View>

            <Ionicons name="chevron-forward" size={16} color="#ccc" />
          </View>

          {/* Address + rainfall chip */}
          <View style={styles.addressRow}>
            {item.address ? (
              <>
                <Ionicons name="location-outline" size={13} color="#999" />
                <Text style={styles.cardAddress} numberOfLines={1}>{item.address}</Text>
              </>
            ) : null}
            {item.rainfall_now_mm != null ? (
              <View style={styles.rainfallChip}>
                <Ionicons name="rainy-outline" size={12} color="#2E75B6" />
                <Text style={styles.rainfallChipText}>{item.rainfall_now_mm} mm</Text>
              </View>
            ) : null}
          </View>

          {/* 行動建議（僅風險 ≥ 50% 顯示）*/}
          {advice ? (
            <View style={[styles.adviceBox, { backgroundColor: advice.bg, borderColor: advice.border }]}>
              <Text style={styles.adviceIcon}>{advice.icon}</Text>
              <View style={{ flex: 1 }}>
                <Text style={styles.adviceLabel}>行動建議</Text>
                <Text style={styles.adviceText}>{advice.text}</Text>
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

      {(listLoading && !refreshing) ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color="#2E75B6" />
          <Text style={styles.loadingText}>載入中...</Text>
        </View>
      ) : listError ? (
        <View style={styles.center}>
          <Ionicons name="cloud-offline-outline" size={48} color="#ccc" />
          <Text style={styles.errorText}>{listError}</Text>
          <TouchableOpacity style={styles.retryBtn} onPress={fetchProperties}>
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
          onComplete={() => { setAddVisible(false); fetchProperties(); }}
          onCancel={() => setAddVisible(false)}
        />
      </Modal>

      {/* ── Edit：Step 1 表單 ── */}
      <Modal
        visible={editStep === 1}
        transparent
        animationType="slide"
        onRequestClose={() => { setEditStep(0); setEditingProperty(null); }}
      >
        <KeyboardAvoidingView
          style={styles.modalOverlay}
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        >
          <View style={styles.modalBox}>
            <View style={styles.editHeader}>
              <Text style={styles.modalTitle}>編輯財產</Text>
              <TouchableOpacity onPress={() => { setEditStep(0); setEditingProperty(null); }}>
                <Ionicons name="close" size={22} color="#888" />
              </TouchableOpacity>
            </View>

            <Text style={styles.inputLabel}>財產名稱 *</Text>
            <TextInput style={styles.input} value={editName} onChangeText={setEditName} autoFocus />
            <Text style={styles.inputLabel}>地址（選填）</Text>
            <TextInput style={styles.input} value={editAddress} onChangeText={setEditAddress} />

            <TouchableOpacity style={styles.relocateBtn} onPress={() => setEditStep(2)}>
              <Ionicons name="map-outline" size={16} color="#2E75B6" />
              <Text style={styles.relocateBtnText}>重新選擇位置</Text>
              <Text style={styles.relocateCoord}>{editLat.toFixed(4)}, {editLng.toFixed(4)}</Text>
            </TouchableOpacity>

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
          </View>
        </KeyboardAvoidingView>
      </Modal>

      {/* ── Edit：Step 2 地圖重新選點 ── */}
      <Modal visible={editStep === 2} animationType="slide" onRequestClose={() => setEditStep(1)}>
        <View style={styles.mapContainer}>
          <MapView
            style={styles.mapFull}
            initialRegion={{
              latitude: editLat || TAIWAN_CENTER.latitude,
              longitude: editLng || TAIWAN_CENTER.longitude,
              latitudeDelta: 0.05,
              longitudeDelta: 0.05,
            }}
            onRegionChangeComplete={(region) => {
              setEditLat(region.latitude);
              setEditLng(region.longitude);
            }}
          />
          <View style={StyleSheet.absoluteFillObject} pointerEvents="none">
            <View style={styles.pin}>
              <View style={styles.pinHead} />
              <View style={styles.pinTail} />
            </View>
          </View>
          <View style={styles.pickerBottom}>
            <View style={styles.pickerCoordBox}>
              <Ionicons name="location" size={16} color="#2E75B6" />
              <Text style={styles.coordText}>
                {editLat.toFixed(5)},  {editLng.toFixed(5)}
              </Text>
            </View>
            <Text style={styles.pickerHint}>拖動地圖來選擇新位置</Text>
            <View style={styles.pickerBtns}>
              <TouchableOpacity style={styles.cancelBtn} onPress={() => setEditStep(1)}>
                <Text style={styles.cancelBtnText}>返回</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.confirmBtn} onPress={() => setEditStep(1)}>
                <Ionicons name="checkmark" size={18} color="#fff" />
                <Text style={styles.confirmBtnText}>確認位置</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
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

  mapContainer: { flex: 1 },
  mapFull: { flex: 1 },
  pin: {
    position: 'absolute', top: '50%', left: '50%',
    marginLeft: -(PIN_HEAD / 2), marginTop: -PIN_HEIGHT, alignItems: 'center',
  },
  pinHead: {
    width: PIN_HEAD, height: PIN_HEAD, borderRadius: PIN_HEAD / 2,
    backgroundColor: '#C00000', borderWidth: 2.5, borderColor: '#fff',
    shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.35, shadowRadius: 4, elevation: 5,
  },
  pinTail: { width: 3, height: PIN_TAIL, backgroundColor: '#C00000' },
  pickerBottom: {
    backgroundColor: '#fff', paddingHorizontal: 20, paddingTop: 16, paddingBottom: 36, gap: 10,
    shadowColor: '#000', shadowOffset: { width: 0, height: -3 }, shadowOpacity: 0.08, shadowRadius: 8, elevation: 10,
  },
  pickerCoordBox: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: 6, backgroundColor: '#EBF3FB', paddingVertical: 8, borderRadius: 10,
  },
  coordText: { fontSize: 14, color: '#2E75B6', fontWeight: '600' },
  pickerHint: { textAlign: 'center', fontSize: 12, color: '#aaa' },
  pickerBtns: { flexDirection: 'row', gap: 12, marginTop: 4 },

  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', paddingHorizontal: 24 },
  modalBox: {
    backgroundColor: '#fff', borderRadius: 20, padding: 24,
    shadowColor: '#000', shadowOffset: { width: 0, height: 8 }, shadowOpacity: 0.15, shadowRadius: 16, elevation: 12,
  },
  modalTitle: { fontSize: 20, fontWeight: '700', color: '#1A1A2E', textAlign: 'center', marginBottom: 10 },
  editHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 },
  inputLabel: { fontSize: 13, color: '#555', fontWeight: '600', marginBottom: 6, marginTop: 12 },
  input: {
    borderWidth: 1.5, borderColor: '#E0E0E0', borderRadius: 10,
    paddingHorizontal: 14, paddingVertical: 11, fontSize: 15, color: '#222', backgroundColor: '#FAFAFA',
  },
  relocateBtn: { flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: '#EBF3FB', borderRadius: 10, padding: 12, marginTop: 14 },
  relocateBtnText: { fontSize: 14, color: '#2E75B6', fontWeight: '600', flex: 1 },
  relocateCoord: { fontSize: 11, color: '#888' },
  formErrorBox: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 10, backgroundColor: '#FFF0F0', padding: 10, borderRadius: 8 },
  formErrorText: { color: '#C00000', fontSize: 13, flex: 1 },
  modalBtns: { flexDirection: 'row', gap: 12, marginTop: 20 },
  cancelBtn: { flex: 1, paddingVertical: 13, borderRadius: 12, backgroundColor: '#F0F0F0', alignItems: 'center' },
  cancelBtnText: { fontSize: 15, color: '#666', fontWeight: '600' },
  confirmBtn: { flex: 2, paddingVertical: 13, borderRadius: 12, backgroundColor: '#2E75B6', alignItems: 'center', flexDirection: 'row', justifyContent: 'center', gap: 6 },
  confirmBtnText: { fontSize: 15, color: '#fff', fontWeight: '700' },
  deleteBtn: { flex: 1, paddingVertical: 13, borderRadius: 12, backgroundColor: '#FFF0F0', alignItems: 'center', flexDirection: 'row', justifyContent: 'center', gap: 6, borderWidth: 1.5, borderColor: '#FCCCC' },
  deleteBtnText: { fontSize: 15, color: '#C00000', fontWeight: '600' },
});
