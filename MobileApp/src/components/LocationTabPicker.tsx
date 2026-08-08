import { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  ActivityIndicator, Modal,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import MapView, { Region } from 'react-native-maps';
import { apiFetch } from '../lib/api';

const TAIWAN_CENTER: Region = {
  latitude: 23.5, longitude: 121.0,
  latitudeDelta: 5, longitudeDelta: 5,
};

const PIN_HEAD = 26;
const PIN_TAIL = 14;
const PIN_HEIGHT = PIN_HEAD + PIN_TAIL;

interface Props {
  initialLat?: number;
  initialLng?: number;
  initialAddress?: string;
  onLocationChange: (lat: number, lng: number, address: string | null) => void;
}

export default function LocationTabPicker({
  initialLat,
  initialLng,
  initialAddress,
  onLocationChange,
}: Props) {
  const [activeTab, setActiveTab] = useState<'address' | 'map'>('address');

  // Address geocoding
  const [addressInput, setAddressInput] = useState(initialAddress ?? '');
  const [geocoding, setGeocoding] = useState(false);
  const [geocodeResult, setGeocodeResult] = useState<{
    lat: number; lng: number; formatted_address: string;
  } | null>(null);
  const [geocodeError, setGeocodeError] = useState<string | null>(null);

  // Map
  const [mapVisible, setMapVisible] = useState(false);
  const [mapLat, setMapLat] = useState(initialLat ?? TAIWAN_CENTER.latitude);
  const [mapLng, setMapLng] = useState(initialLng ?? TAIWAN_CENTER.longitude);
  const [mapConfirmed, setMapConfirmed] = useState(false);
  const [mapAddress, setMapAddress] = useState<string | null>(null);
  const [reverseGeocoding, setReverseGeocoding] = useState(false);

  const handleGeocode = async () => {
    const q = addressInput.trim();
    if (!q) return;
    setGeocoding(true);
    setGeocodeError(null);
    setGeocodeResult(null);
    try {
      const resp = await apiFetch(`/api/geocode?address=${encodeURIComponent(q)}`);
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail ?? '地址查詢失敗');
      setGeocodeResult(data);
      onLocationChange(data.lat, data.lng, addressInput.trim());
    } catch (e: any) {
      setGeocodeError(e.message ?? '地址查詢失敗');
    } finally {
      setGeocoding(false);
    }
  };

  const handleMapConfirm = async () => {
    setMapConfirmed(true);
    setMapVisible(false);
    onLocationChange(mapLat, mapLng, null);
    setReverseGeocoding(true);
    try {
      const resp = await apiFetch(`/api/reverse-geocode?lat=${mapLat}&lng=${mapLng}`);
      const data = await resp.json();
      if (resp.ok) {
        setMapAddress(data.formatted_address ?? null);
        onLocationChange(mapLat, mapLng, data.formatted_address ?? null);
      }
    } catch (_) {}
    setReverseGeocoding(false);
  };

  return (
    <View>
      {/* Tab 切換 */}
      <View style={styles.tabs}>
        {(['address', 'map'] as const).map((tab) => (
          <TouchableOpacity
            key={tab}
            style={[styles.tab, activeTab === tab && styles.tabActive]}
            onPress={() => setActiveTab(tab)}
            activeOpacity={0.7}
          >
            <Text style={[styles.tabText, activeTab === tab && styles.tabTextActive]}>
              {tab === 'address' ? '輸入地址' : '地圖選點'}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* 輸入地址 */}
      {activeTab === 'address' && (
        <View>
          <View style={styles.addressRow}>
            <TextInput
              style={[styles.input, styles.addressInput]}
              placeholder="例：台北市信義區市府路1號"
              value={addressInput}
              onChangeText={(t) => {
                setAddressInput(t);
                if (geocodeResult) setGeocodeResult(null);
                if (geocodeError) setGeocodeError(null);
              }}
              returnKeyType="search"
              onSubmitEditing={handleGeocode}
            />
            <TouchableOpacity
              style={[styles.geocodeBtn, (!addressInput.trim() || geocoding) && styles.geocodeBtnDisabled]}
              onPress={handleGeocode}
              disabled={geocoding || !addressInput.trim()}
            >
              {geocoding
                ? <ActivityIndicator color="#fff" size="small" />
                : <Ionicons name="search" size={18} color="#fff" />
              }
            </TouchableOpacity>
          </View>

          {geocodeError ? (
            <View style={styles.infoBox}>
              <Ionicons name="alert-circle-outline" size={14} color="#C00000" />
              <Text style={styles.infoBoxTextError}>{geocodeError}</Text>
            </View>
          ) : geocodeResult ? (
            <View style={[styles.infoBox, styles.infoBoxSuccess]}>
              <Ionicons name="checkmark-circle" size={14} color="#27AE60" />
              <View style={{ flex: 1 }}>
                <Text style={styles.infoBoxTextSuccess} numberOfLines={2}>
                  {geocodeResult.formatted_address}
                </Text>
                <Text style={styles.infoBoxCoord}>
                  {geocodeResult.lat.toFixed(5)}, {geocodeResult.lng.toFixed(5)}
                </Text>
              </View>
            </View>
          ) : null}
        </View>
      )}

      {/* 地圖選點 */}
      {activeTab === 'map' && (
        <TouchableOpacity
          style={[styles.mapPickerBtn, mapConfirmed && styles.mapPickerBtnConfirmed]}
          onPress={() => setMapVisible(true)}
          activeOpacity={0.8}
        >
          <Ionicons
            name="map-outline"
            size={18}
            color={mapConfirmed ? '#27AE60' : '#2E75B6'}
          />
          <Text
            style={[styles.mapPickerBtnText, mapConfirmed && styles.mapPickerBtnTextConfirmed]}
            numberOfLines={1}
          >
            {mapConfirmed
              ? (reverseGeocoding ? '地址解析中…' : (mapAddress ?? `${mapLat.toFixed(4)}, ${mapLng.toFixed(4)}`))
              : '開啟地圖選點'}
          </Text>
          {mapConfirmed && !reverseGeocoding && <Ionicons name="checkmark-circle" size={16} color="#27AE60" />}
          {mapConfirmed && reverseGeocoding && <ActivityIndicator size="small" color="#27AE60" />}
          {!mapConfirmed && <Ionicons name="chevron-forward" size={16} color="#2E75B6" />}
        </TouchableOpacity>
      )}

      {/* 地圖全螢幕 Modal */}
      <Modal visible={mapVisible} animationType="slide" onRequestClose={() => setMapVisible(false)}>
        <View style={styles.mapContainer}>
          <MapView
            style={styles.mapFull}
            initialRegion={
              (initialLat && initialLng)
                ? { latitude: initialLat, longitude: initialLng, latitudeDelta: 0.05, longitudeDelta: 0.05 }
                : TAIWAN_CENTER
            }
            onRegionChangeComplete={(r) => { setMapLat(r.latitude); setMapLng(r.longitude); }}
          />
          <View style={StyleSheet.absoluteFillObject} pointerEvents="none">
            <View style={styles.pin}>
              <View style={styles.pinHead} />
              <View style={styles.pinTail} />
            </View>
          </View>
          <View style={styles.pickerBottom}>
            <View style={styles.coordBox}>
              <Ionicons name="location" size={16} color="#2E75B6" />
              <Text style={styles.coordText}>{mapLat.toFixed(5)},  {mapLng.toFixed(5)}</Text>
            </View>
            <Text style={styles.pickerHint}>拖動地圖選擇財產位置</Text>
            <View style={styles.pickerBtns}>
              <TouchableOpacity style={styles.cancelBtn} onPress={() => setMapVisible(false)}>
                <Text style={styles.cancelBtnText}>取消</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.confirmBtn} onPress={handleMapConfirm}>
                <Ionicons name="checkmark" size={18} color="#fff" />
                <Text style={styles.confirmBtnText}>選擇此位置</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  tabs: {
    flexDirection: 'row', borderRadius: 10, overflow: 'hidden',
    borderWidth: 1.5, borderColor: '#2E75B6', marginBottom: 12,
  },
  tab: {
    flex: 1, paddingVertical: 9, alignItems: 'center',
    backgroundColor: '#fff',
  },
  tabActive: { backgroundColor: '#2E75B6' },
  tabText: { fontSize: 13, fontWeight: '600', color: '#2E75B6' },
  tabTextActive: { color: '#fff' },

  addressRow: { flexDirection: 'row', gap: 8, alignItems: 'stretch' },
  addressInput: { flex: 1 },
  input: {
    borderWidth: 1.5, borderColor: '#E0E0E0', borderRadius: 12,
    paddingHorizontal: 14, paddingVertical: 12, fontSize: 15,
    color: '#222', backgroundColor: '#fff',
  },
  geocodeBtn: {
    width: 48, backgroundColor: '#2E75B6', borderRadius: 12,
    alignItems: 'center', justifyContent: 'center',
  },
  geocodeBtnDisabled: { backgroundColor: '#B0C8E0' },

  infoBox: {
    flexDirection: 'row', alignItems: 'flex-start', gap: 8,
    backgroundColor: '#FFF0F0', padding: 12, borderRadius: 10, marginTop: 8,
  },
  infoBoxSuccess: { backgroundColor: '#E8F8EF' },
  infoBoxTextError: { fontSize: 13, color: '#C00000', flex: 1 },
  infoBoxTextSuccess: { fontSize: 13, color: '#1A6B3A', fontWeight: '500', flex: 1 },
  infoBoxCoord: { fontSize: 11, color: '#888', marginTop: 2 },

  mapPickerBtn: {
    flexDirection: 'row', alignItems: 'center', gap: 10,
    backgroundColor: '#EBF3FB', borderRadius: 12, padding: 14,
    borderWidth: 1.5, borderColor: '#C5DCEF',
  },
  mapPickerBtnConfirmed: { backgroundColor: '#E8F8EF', borderColor: '#A5D6B8' },
  mapPickerBtnText: { flex: 1, fontSize: 14, color: '#2E75B6', fontWeight: '600' },
  mapPickerBtnTextConfirmed: { color: '#1A6B3A' },

  mapContainer: { flex: 1 },
  mapFull: { flex: 1 },
  pin: {
    position: 'absolute', top: '50%', left: '50%',
    marginLeft: -(PIN_HEAD / 2), marginTop: -PIN_HEIGHT, alignItems: 'center',
  },
  pinHead: {
    width: PIN_HEAD, height: PIN_HEAD, borderRadius: PIN_HEAD / 2,
    backgroundColor: '#C00000', borderWidth: 2.5, borderColor: '#fff',
    shadowColor: '#000', shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.35, shadowRadius: 4, elevation: 5,
  },
  pinTail: { width: 3, height: PIN_TAIL, backgroundColor: '#C00000' },
  pickerBottom: {
    backgroundColor: '#fff', paddingHorizontal: 20, paddingTop: 16, paddingBottom: 36, gap: 10,
    shadowColor: '#000', shadowOffset: { width: 0, height: -3 },
    shadowOpacity: 0.08, shadowRadius: 8, elevation: 10,
  },
  coordBox: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: 6, backgroundColor: '#EBF3FB', paddingVertical: 8, borderRadius: 10,
  },
  coordText: { fontSize: 14, color: '#2E75B6', fontWeight: '600' },
  pickerHint: { textAlign: 'center', fontSize: 12, color: '#aaa' },
  pickerBtns: { flexDirection: 'row', gap: 12, marginTop: 4 },
  cancelBtn: {
    flex: 1, paddingVertical: 13, borderRadius: 12,
    backgroundColor: '#F0F0F0', alignItems: 'center',
  },
  cancelBtnText: { fontSize: 15, color: '#666', fontWeight: '600' },
  confirmBtn: {
    flex: 2, paddingVertical: 13, borderRadius: 12, backgroundColor: '#2E75B6',
    alignItems: 'center', flexDirection: 'row', justifyContent: 'center', gap: 6,
  },
  confirmBtnText: { fontSize: 15, color: '#fff', fontWeight: '700' },
});
