import { useState, useEffect } from 'react';
import {
  View, TouchableOpacity, Text, StyleSheet,
  ActivityIndicator, FlatList, RefreshControl,
  Modal, TextInput, KeyboardAvoidingView, Platform,
} from 'react-native';
import MapView, { Region } from 'react-native-maps';

interface Property {
  id: string;
  name: string;
  address: string | null;
  latitude: number;
  longitude: number;
}

interface Threshold {
  threshold_1h: number | null;
  threshold_3h: number | null;
  threshold_6h: number | null;
  source: string;
}

interface RainfallResult {
  station_name: string;
  distance_km: number;
  rainfall_mm: number;
  observed_at: string;
}

const TAIWAN_CENTER: Region = {
  latitude: 23.5,
  longitude: 121.0,
  latitudeDelta: 5,
  longitudeDelta: 5,
};

export default function PropertyScreen() {
  const [viewMode, setViewMode] = useState<'map' | 'list'>('map');

  // 地圖模式狀態
  const [loading, setLoading] = useState(false);
  const [rainfall, setRainfall] = useState<RainfallResult | null>(null);
  const [mapError, setMapError] = useState<string | null>(null);

  // 列表模式狀態
  const [properties, setProperties] = useState<Property[]>([]);
  const [listLoading, setListLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [listError, setListError] = useState<string | null>(null);
  const [thresholds, setThresholds] = useState<Record<string, Threshold>>({});

  // 新增財產：2 步驟流程
  const [addStep, setAddStep] = useState<0 | 1 | 2>(0); // 0=關閉, 1=選地點, 2=填名稱
  const [selectedLat, setSelectedLat] = useState(TAIWAN_CENTER.latitude);
  const [selectedLng, setSelectedLng] = useState(TAIWAN_CENTER.longitude);
  const [formName, setFormName] = useState('');
  const [formAddress, setFormAddress] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const base = process.env.EXPO_PUBLIC_API_URL;

  const fetchProperties = async () => {
    setListLoading(true);
    setListError(null);
    try {
      const resp = await fetch(`${base}/api/properties`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      setProperties(data);

      const thresholdMap: Record<string, Threshold> = {};
      await Promise.all(
        data.map(async (p: Property) => {
          try {
            const tr = await fetch(`${base}/api/threshold?lat=${p.latitude}&lng=${p.longitude}`);
            if (tr.ok) {
              thresholdMap[p.id] = await tr.json();
            }
          } catch {
            // ignore
          }
        })
      );
      setThresholds(thresholdMap);
    } catch (e: any) {
      setListError(e.message ?? '無法載入財產');
    } finally {
      setListLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    if (viewMode === 'list') {
      fetchProperties();
    }
  }, [viewMode]);

  const onRefresh = () => {
    setRefreshing(true);
    fetchProperties();
  };

  const openPicker = () => {
    setSelectedLat(TAIWAN_CENTER.latitude);
    setSelectedLng(TAIWAN_CENTER.longitude);
    setFormName('');
    setFormAddress('');
    setFormError(null);
    setAddStep(1);
  };

  const confirmLocation = () => {
    setFormError(null);
    setAddStep(2);
  };

  const addProperty = async () => {
    if (!formName.trim()) { setFormError('請輸入財產名稱'); return; }
    setSubmitting(true);
    setFormError(null);
    try {
      const resp = await fetch(`${base}/api/properties`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: formName.trim(),
          address: formAddress.trim() || null,
          latitude: selectedLat,
          longitude: selectedLng,
          type: 'house',
        }),
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail ?? `HTTP ${resp.status}`);
      }
      setAddStep(0);
      fetchProperties();
    } catch (e: any) {
      setFormError(e.message ?? '新增失敗');
    } finally {
      setSubmitting(false);
    }
  };

  async function testRainfall() {
    setLoading(true);
    setMapError(null);
    setRainfall(null);
    try {
      const resp = await fetch(`${base}/api/test-rainfall?lat=25.04&lng=121.51`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data: RainfallResult = await resp.json();
      setRainfall(data);
    } catch (e: any) {
      setMapError(e.message ?? '連線失敗');
    } finally {
      setLoading(false);
    }
  }

  const renderProperty = ({ item }: { item: Property }) => {
    const t = thresholds[item.id];
    return (
      <View style={styles.card}>
        <Text style={styles.cardName}>{item.name}</Text>
        {item.address && (
          <Text style={styles.cardAddress}>{item.address}</Text>
        )}
        {t ? (
          <View style={styles.thresholdRow}>
            <Text style={styles.thresholdLabel}>
              門檻（{t.source === 'corrected' ? '校正後' : 'WRA 原始'}）
            </Text>
            <Text style={styles.thresholdValues}>
              1H {t.threshold_1h ?? '-'}mm　3H {t.threshold_3h ?? '-'}mm　6H {t.threshold_6h ?? '-'}mm
            </Text>
          </View>
        ) : (
          <Text style={styles.noThreshold}>門檻載入中...</Text>
        )}
      </View>
    );
  };

  return (
    <View style={{ flex: 1 }}>
      <View style={styles.toggleRow}>
        <TouchableOpacity
          style={[styles.toggleBtn, viewMode === 'map' && styles.active]}
          onPress={() => setViewMode('map')}
        >
          <Text style={viewMode === 'map' ? styles.activeText : undefined}>地圖</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.toggleBtn, viewMode === 'list' && styles.active]}
          onPress={() => setViewMode('list')}
        >
          <Text style={viewMode === 'list' ? styles.activeText : undefined}>列表</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.addBtn} onPress={openPicker}>
          <Text style={styles.addBtnText}>＋</Text>
        </TouchableOpacity>
      </View>

      {/* Step 1: 地圖選點 */}
      <Modal
        visible={addStep === 1}
        animationType="slide"
        onRequestClose={() => setAddStep(0)}
      >
        <View style={{ flex: 1 }}>
          <MapView
            style={{ flex: 1 }}
            initialRegion={TAIWAN_CENTER}
            onRegionChangeComplete={(region) => {
              setSelectedLat(region.latitude);
              setSelectedLng(region.longitude);
            }}
          />
          {/* 固定圖釘：tip 在地圖中央 */}
          <View style={styles.pinOverlay} pointerEvents="none">
            <View style={styles.pin}>
              <View style={styles.pinHead} />
              <View style={styles.pinTail} />
            </View>
          </View>
          {/* 底部操作區 */}
          <View style={styles.pickerBottom}>
            <Text style={styles.coordText}>
              {selectedLat.toFixed(5)}, {selectedLng.toFixed(5)}
            </Text>
            <View style={styles.pickerBtns}>
              <TouchableOpacity style={styles.cancelBtn} onPress={() => setAddStep(0)}>
                <Text style={styles.cancelBtnText}>取消</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.confirmBtn} onPress={confirmLocation}>
                <Text style={styles.confirmBtnText}>選擇此位置</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {/* Step 2: 填寫名稱 */}
      <Modal
        visible={addStep === 2}
        transparent
        animationType="fade"
        onRequestClose={() => setAddStep(1)}
      >
        <KeyboardAvoidingView
          style={styles.modalOverlay}
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        >
          <View style={styles.modalBox}>
            <Text style={styles.modalTitle}>新增財產</Text>
            <Text style={styles.coordSummary}>
              位置：{selectedLat.toFixed(5)}, {selectedLng.toFixed(5)}
            </Text>
            <Text style={styles.inputLabel}>財產名稱 *</Text>
            <TextInput
              style={styles.input}
              placeholder="例：台北辦公室"
              value={formName}
              onChangeText={setFormName}
              autoFocus
            />
            <Text style={styles.inputLabel}>地址（選填）</Text>
            <TextInput
              style={styles.input}
              placeholder="例：台北市信義區市府路1號"
              value={formAddress}
              onChangeText={setFormAddress}
            />
            {formError && (
              <Text style={styles.formErrorText}>{formError}</Text>
            )}
            <View style={styles.modalBtns}>
              <TouchableOpacity
                style={styles.cancelBtn}
                onPress={() => setAddStep(1)}
                disabled={submitting}
              >
                <Text style={styles.cancelBtnText}>返回</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.confirmBtn}
                onPress={addProperty}
                disabled={submitting}
              >
                {submitting
                  ? <ActivityIndicator color="#fff" />
                  : <Text style={styles.confirmBtnText}>確認新增</Text>
                }
              </TouchableOpacity>
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>

      {viewMode === 'map' && (
        <View style={{ flex: 1 }}>
          <MapView
            style={{ flex: 1 }}
            initialRegion={{
              latitude: 25.0339,
              longitude: 121.5645,
              latitudeDelta: 0.05,
              longitudeDelta: 0.05,
            }}
          />
          <View style={styles.overlay}>
            <TouchableOpacity style={styles.testBtn} onPress={testRainfall} disabled={loading}>
              {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.testBtnText}>測試雨量</Text>}
            </TouchableOpacity>
            {rainfall && (
              <View style={styles.resultBox}>
                <Text style={styles.resultText}>
                  最近雨量站：{rainfall.station_name}，當前雨量：{rainfall.rainfall_mm} mm
                </Text>
              </View>
            )}
            {mapError && (
              <View style={styles.resultBox}>
                <Text style={[styles.resultText, { color: 'red' }]}>{mapError}</Text>
              </View>
            )}
          </View>
        </View>
      )}

      {viewMode === 'list' && (
        <>
          {listLoading && !refreshing ? (
            <View style={styles.center}>
              <ActivityIndicator size="large" color="#2E75B6" />
            </View>
          ) : listError ? (
            <View style={styles.center}>
              <Text style={styles.errorText}>{listError}</Text>
              <TouchableOpacity style={styles.testBtn} onPress={fetchProperties}>
                <Text style={styles.testBtnText}>重試</Text>
              </TouchableOpacity>
            </View>
          ) : properties.length === 0 ? (
            <View style={styles.center}>
              <Text style={styles.emptyText}>尚無財產，請新增</Text>
            </View>
          ) : (
            <FlatList
              data={properties}
              keyExtractor={(item) => item.id}
              contentContainerStyle={{ padding: 16, gap: 12 }}
              refreshControl={
                <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
              }
              renderItem={renderProperty}
            />
          )}
        </>
      )}
    </View>
  );
}

const PIN_HEAD = 26;
const PIN_TAIL = 14;
const PIN_HEIGHT = PIN_HEAD + PIN_TAIL;

const styles = StyleSheet.create({
  toggleRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    paddingTop: 12,
    paddingBottom: 8,
    backgroundColor: '#fff',
    gap: 8,
  },
  toggleBtn: {
    paddingHorizontal: 24,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: '#eee',
  },
  active: {
    backgroundColor: '#2E75B6',
  },
  activeText: {
    color: '#fff',
    fontWeight: '600',
  },
  addBtn: {
    position: 'absolute',
    right: 16,
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 20,
    backgroundColor: '#2E75B6',
  },
  addBtnText: {
    color: '#fff',
    fontSize: 18,
    lineHeight: 22,
    fontWeight: '700',
  },
  // 圖釘
  pinOverlay: {
    ...StyleSheet.absoluteFillObject,
  },
  pin: {
    position: 'absolute',
    top: '50%',
    left: '50%',
    marginLeft: -(PIN_HEAD / 2),
    marginTop: -PIN_HEIGHT,
    alignItems: 'center',
  },
  pinHead: {
    width: PIN_HEAD,
    height: PIN_HEAD,
    borderRadius: PIN_HEAD / 2,
    backgroundColor: '#C00000',
    borderWidth: 2,
    borderColor: '#fff',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 3,
    elevation: 4,
  },
  pinTail: {
    width: 3,
    height: PIN_TAIL,
    backgroundColor: '#C00000',
  },
  // 地圖選點底部
  pickerBottom: {
    backgroundColor: '#fff',
    paddingHorizontal: 20,
    paddingTop: 14,
    paddingBottom: 32,
    gap: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -2 },
    shadowOpacity: 0.08,
    shadowRadius: 6,
    elevation: 8,
  },
  coordText: {
    textAlign: 'center',
    fontSize: 13,
    color: '#555',
    fontVariant: ['tabular-nums'],
  },
  pickerBtns: {
    flexDirection: 'row',
    gap: 12,
  },
  // Step 2 modal
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.45)',
    justifyContent: 'center',
    paddingHorizontal: 24,
  },
  modalBox: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 24,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#222',
    marginBottom: 4,
    textAlign: 'center',
  },
  coordSummary: {
    fontSize: 12,
    color: '#888',
    textAlign: 'center',
    marginBottom: 16,
  },
  inputLabel: {
    fontSize: 13,
    color: '#555',
    marginBottom: 4,
    marginTop: 10,
  },
  input: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 15,
    color: '#222',
    backgroundColor: '#fafafa',
  },
  formErrorText: {
    color: '#C00000',
    fontSize: 13,
    marginTop: 10,
    textAlign: 'center',
  },
  modalBtns: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 20,
  },
  cancelBtn: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 10,
    backgroundColor: '#eee',
    alignItems: 'center',
  },
  cancelBtnText: {
    fontSize: 15,
    color: '#555',
    fontWeight: '600',
  },
  confirmBtn: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 10,
    backgroundColor: '#2E75B6',
    alignItems: 'center',
  },
  confirmBtnText: {
    fontSize: 15,
    color: '#fff',
    fontWeight: '600',
  },
  // 主畫面
  overlay: {
    position: 'absolute',
    top: 12,
    left: 16,
    right: 16,
    alignItems: 'center',
    gap: 8,
  },
  testBtn: {
    backgroundColor: '#2E75B6',
    paddingHorizontal: 24,
    paddingVertical: 10,
    borderRadius: 20,
    minWidth: 100,
    alignItems: 'center',
  },
  testBtnText: {
    color: '#fff',
    fontWeight: '600',
  },
  resultBox: {
    backgroundColor: 'rgba(255,255,255,0.92)',
    borderRadius: 10,
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  resultText: {
    fontSize: 14,
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 12,
  },
  emptyText: {
    fontSize: 16,
    color: '#888',
  },
  errorText: {
    color: '#C00000',
    fontSize: 16,
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 3,
    elevation: 2,
  },
  cardName: {
    fontSize: 16,
    fontWeight: '700',
    color: '#222',
    marginBottom: 4,
  },
  cardAddress: {
    fontSize: 13,
    color: '#666',
    marginBottom: 8,
  },
  thresholdRow: {
    marginTop: 8,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: '#f0f0f0',
    gap: 2,
  },
  thresholdLabel: {
    fontSize: 12,
    color: '#888',
  },
  thresholdValues: {
    fontSize: 13,
    color: '#2E75B6',
    fontWeight: '600',
  },
  noThreshold: {
    fontSize: 12,
    color: '#aaa',
    marginTop: 8,
  },
});
