import { useState } from 'react';
import {
  View, TouchableOpacity, Text, StyleSheet,
  ActivityIndicator, Modal, TextInput,
  KeyboardAvoidingView, Platform,
} from 'react-native';
import MapView, { Region } from 'react-native-maps';

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

const PIN_HEAD = 26;
const PIN_TAIL = 14;
const PIN_HEIGHT = PIN_HEAD + PIN_TAIL;

export default function MapScreen() {
  const [loading, setLoading] = useState(false);
  const [rainfall, setRainfall] = useState<RainfallResult | null>(null);
  const [mapError, setMapError] = useState<string | null>(null);

  // 新增財產：2 步驟
  const [addStep, setAddStep] = useState<0 | 1 | 2>(0);
  const [selectedLat, setSelectedLat] = useState(TAIWAN_CENTER.latitude);
  const [selectedLng, setSelectedLng] = useState(TAIWAN_CENTER.longitude);
  const [formName, setFormName] = useState('');
  const [formAddress, setFormAddress] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const base = process.env.EXPO_PUBLIC_API_URL;

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

  const openPicker = () => {
    setSelectedLat(TAIWAN_CENTER.latitude);
    setSelectedLng(TAIWAN_CENTER.longitude);
    setFormName('');
    setFormAddress('');
    setFormError(null);
    setAddStep(1);
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
    } catch (e: any) {
      setFormError(e.message ?? '新增失敗');
    } finally {
      setSubmitting(false);
    }
  };

  return (
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
        <TouchableOpacity style={styles.addBtn} onPress={openPicker}>
          <Text style={styles.addBtnText}>＋ 新增財產</Text>
        </TouchableOpacity>
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
          <View style={styles.pinOverlay} pointerEvents="none">
            <View style={styles.pin}>
              <View style={styles.pinHead} />
              <View style={styles.pinTail} />
            </View>
          </View>
          <View style={styles.pickerBottom}>
            <Text style={styles.coordText}>
              {selectedLat.toFixed(5)}, {selectedLng.toFixed(5)}
            </Text>
            <View style={styles.pickerBtns}>
              <TouchableOpacity style={styles.cancelBtn} onPress={() => setAddStep(0)}>
                <Text style={styles.cancelBtnText}>取消</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.confirmBtn} onPress={() => { setFormError(null); setAddStep(2); }}>
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
            {formError && <Text style={styles.formErrorText}>{formError}</Text>}
            <View style={styles.modalBtns}>
              <TouchableOpacity style={styles.cancelBtn} onPress={() => setAddStep(1)} disabled={submitting}>
                <Text style={styles.cancelBtnText}>返回</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.confirmBtn} onPress={addProperty} disabled={submitting}>
                {submitting
                  ? <ActivityIndicator color="#fff" />
                  : <Text style={styles.confirmBtnText}>確認新增</Text>
                }
              </TouchableOpacity>
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  overlay: {
    position: 'absolute',
    top: 12,
    left: 16,
    right: 16,
    alignItems: 'center',
    gap: 8,
  },
  addBtn: {
    backgroundColor: '#2E75B6',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 20,
    alignItems: 'center',
  },
  addBtnText: {
    color: '#fff',
    fontWeight: '700',
    fontSize: 14,
  },
  testBtn: {
    backgroundColor: 'rgba(46,117,182,0.85)',
    paddingHorizontal: 20,
    paddingVertical: 8,
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
  },
  pickerBtns: {
    flexDirection: 'row',
    gap: 12,
  },
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
});
