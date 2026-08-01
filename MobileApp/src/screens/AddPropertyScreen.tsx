import { useState } from 'react';
import {
  View, Text, StyleSheet, TextInput, TouchableOpacity,
  ScrollView, ActivityIndicator, Modal,
  KeyboardAvoidingView, Platform,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import MapView, { Region } from 'react-native-maps';
import { apiFetch } from '../lib/api';

// ─── Types ────────────────────────────────────────────────────────────────────

type PropertyType = 'house' | 'car' | 'warehouse' | 'other';

interface Props {
  onComplete: () => void;
  onCancel: () => void;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const TYPE_OPTIONS: { key: PropertyType; label: string; icon: string }[] = [
  { key: 'house',     label: '住家', icon: 'home-outline'     },
  { key: 'car',       label: '車輛', icon: 'car-outline'      },
  { key: 'warehouse', label: '倉庫', icon: 'business-outline' },
  { key: 'other',     label: '其他', icon: 'cube-outline'     },
];

const TAIWAN_CENTER: Region = {
  latitude: 23.5, longitude: 121.0,
  latitudeDelta: 5, longitudeDelta: 5,
};

const PIN_HEAD = 26;
const PIN_TAIL = 14;
const PIN_HEIGHT = PIN_HEAD + PIN_TAIL;

// ─── Component ────────────────────────────────────────────────────────────────

export default function AddPropertyScreen({ onComplete, onCancel }: Props) {
  const insets = useSafeAreaInsets();
  // Form fields
  const [name, setName] = useState('');
  const [type, setType] = useState<PropertyType>('house');

  // Address geocoding
  const [addressInput, setAddressInput] = useState('');
  const [geocoding, setGeocoding] = useState(false);
  const [geocodeResult, setGeocodeResult] = useState<{
    lat: number; lng: number; formatted_address: string;
  } | null>(null);
  const [geocodeError, setGeocodeError] = useState<string | null>(null);

  // Map selection
  const [mapVisible, setMapVisible] = useState(false);
  const [mapLat, setMapLat] = useState(TAIWAN_CENTER.latitude);
  const [mapLng, setMapLng] = useState(TAIWAN_CENTER.longitude);
  const [mapConfirmed, setMapConfirmed] = useState(false);
  const [mapAddress, setMapAddress] = useState<string | null>(null);
  const [reverseGeocoding, setReverseGeocoding] = useState(false);

  // Resolved location (address takes priority over map)
  const resolvedLat = geocodeResult?.lat ?? (mapConfirmed ? mapLat : null);
  const resolvedLng = geocodeResult?.lng ?? (mapConfirmed ? mapLng : null);

  // Submit
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // ── Handlers ────────────────────────────────────────────────────────────────

  const handleGeocode = async () => {
    const q = addressInput.trim();
    if (!q) return;
    setGeocoding(true);
    setGeocodeError(null);
    setGeocodeResult(null);
    setMapConfirmed(false);
    try {
      const resp = await apiFetch(`/api/geocode?address=${encodeURIComponent(q)}`);
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail ?? '地址查詢失敗');
      setGeocodeResult(data);
    } catch (e: any) {
      setGeocodeError(e.message ?? '地址查詢失敗');
    } finally {
      setGeocoding(false);
    }
  };

  const handleMapConfirm = async () => {
    setMapConfirmed(true);
    setGeocodeResult(null);
    setGeocodeError(null);
    setMapVisible(false);
    setReverseGeocoding(true);
    try {
      const resp = await apiFetch(`/api/reverse-geocode?lat=${mapLat}&lng=${mapLng}`);
      const data = await resp.json();
      if (resp.ok) setMapAddress(data.formatted_address ?? null);
    } catch (_) {}
    setReverseGeocoding(false);
  };

  const handleSubmit = async () => {
    if (!name.trim()) { setFormError('請輸入財產名稱'); return; }
    if (resolvedLat === null || resolvedLng === null) { setFormError('請選擇財產位置（地址或地圖）'); return; }
    setSubmitting(true);
    setFormError(null);
    try {
      const resp = await apiFetch(`/api/properties`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name.trim(),
          type,
          latitude: resolvedLat,
          longitude: resolvedLng,
          address: geocodeResult ? addressInput.trim() : (mapAddress ?? null),
        }),
      });
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) throw new Error((data as any).detail ?? `HTTP ${resp.status}`);
      onComplete();
    } catch (e: any) {
      setFormError(e.message ?? '新增失敗');
      setSubmitting(false);
    }
  };

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      {/* Header */}
      <View style={[styles.header, { paddingTop: 14 + insets.top }]}>
        <TouchableOpacity onPress={onCancel} style={styles.headerCancel}>
          <Text style={styles.headerCancelText}>取消</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>新增財產</Text>
        <View style={{ width: 52 }} />
      </View>

      <ScrollView
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        {/* 財產名稱 */}
        <Text style={styles.label}>財產名稱 *</Text>
        <TextInput
          style={styles.input}
          placeholder="例：台北辦公室、愛車"
          value={name}
          onChangeText={setName}
          autoFocus
          returnKeyType="next"
        />

        {/* 財產類型 */}
        <Text style={styles.label}>財產類型 *</Text>
        <View style={styles.typeRow}>
          {TYPE_OPTIONS.map((opt) => (
            <TouchableOpacity
              key={opt.key}
              style={[styles.typeBtn, type === opt.key && styles.typeBtnActive]}
              onPress={() => setType(opt.key)}
              activeOpacity={0.7}
            >
              <Ionicons
                name={opt.icon as any}
                size={22}
                color={type === opt.key ? '#2E75B6' : '#aaa'}
              />
              <Text style={[styles.typeBtnLabel, type === opt.key && styles.typeBtnLabelActive]}>
                {opt.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* 位置 */}
        <Text style={styles.label}>財產位置 *</Text>
        <Text style={styles.sublabel}>方式一：輸入地址自動定位</Text>

        <View style={styles.addressRow}>
          <TextInput
            style={[styles.input, styles.addressInput]}
            placeholder="例：台北市信義區市府路1號"
            value={addressInput}
            onChangeText={(t) => {
              setAddressInput(t);
              if (geocodeResult) { setGeocodeResult(null); }
              if (geocodeError) { setGeocodeError(null); }
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

        {/* Map selection */}
        <Text style={[styles.sublabel, { marginTop: 14 }]}>方式二：在地圖上選點</Text>
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
          <Text style={[styles.mapPickerBtnText, mapConfirmed && styles.mapPickerBtnTextConfirmed]} numberOfLines={1}>
            {mapConfirmed
              ? (reverseGeocoding ? '地址解析中…' : (mapAddress ?? `${mapLat.toFixed(4)}, ${mapLng.toFixed(4)}`))
              : '開啟地圖選點'}
          </Text>
          {mapConfirmed && !reverseGeocoding && <Ionicons name="checkmark-circle" size={16} color="#27AE60" />}
          {mapConfirmed && reverseGeocoding && <ActivityIndicator size="small" color="#27AE60" />}
          {!mapConfirmed && <Ionicons name="chevron-forward" size={16} color="#2E75B6" />}
        </TouchableOpacity>

        {/* 目前座標確認 */}
        {(resolvedLat !== null && resolvedLng !== null) && (
          <View style={styles.resolvedBox}>
            <Ionicons name="location" size={14} color="#2E75B6" />
            <Text style={styles.resolvedText}>
              已選座標：{resolvedLat.toFixed(5)}, {resolvedLng.toFixed(5)}
            </Text>
          </View>
        )}

        {/* Form error */}
        {formError ? (
          <View style={[styles.infoBox, { marginTop: 12 }]}>
            <Ionicons name="alert-circle-outline" size={14} color="#C00000" />
            <Text style={styles.infoBoxTextError}>{formError}</Text>
          </View>
        ) : null}

        {/* Submit */}
        <TouchableOpacity
          style={[styles.submitBtn, (submitting || resolvedLat === null) && styles.submitBtnDisabled]}
          onPress={handleSubmit}
          disabled={submitting || resolvedLat === null}
          activeOpacity={0.85}
        >
          {submitting ? (
            <ActivityIndicator color="#fff" size="small" />
          ) : (
            <>
              <Ionicons name="add-circle-outline" size={20} color="#fff" />
              <Text style={styles.submitBtnText}>確認新增</Text>
            </>
          )}
        </TouchableOpacity>
      </ScrollView>

      {/* Map Modal */}
      <Modal
        visible={mapVisible}
        animationType="slide"
        onRequestClose={() => setMapVisible(false)}
      >
        <View style={styles.mapContainer}>
          <MapView
            style={styles.mapFull}
            initialRegion={
              mapConfirmed
                ? { latitude: mapLat, longitude: mapLng, latitudeDelta: 0.05, longitudeDelta: 0.05 }
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
    </KeyboardAvoidingView>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F0F4F8' },

  header: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    backgroundColor: '#fff', paddingHorizontal: 16, paddingVertical: 14,
    borderBottomWidth: 1, borderBottomColor: '#EAEAEA',
  },
  headerCancel: { paddingHorizontal: 4, paddingVertical: 2 },
  headerCancelText: { fontSize: 16, color: '#2E75B6' },
  headerTitle: { fontSize: 17, fontWeight: '700', color: '#1A1A2E' },

  content: { padding: 20, gap: 4, paddingBottom: 40 },

  label: { fontSize: 14, fontWeight: '600', color: '#333', marginTop: 16, marginBottom: 8 },
  sublabel: { fontSize: 12, color: '#888', marginBottom: 8 },

  input: {
    borderWidth: 1.5, borderColor: '#E0E0E0', borderRadius: 12,
    paddingHorizontal: 14, paddingVertical: 12, fontSize: 15,
    color: '#222', backgroundColor: '#fff',
  },

  typeRow: { flexDirection: 'row', gap: 10 },
  typeBtn: {
    flex: 1, alignItems: 'center', justifyContent: 'center', gap: 6,
    paddingVertical: 14, borderRadius: 12, borderWidth: 1.5,
    borderColor: '#E0E0E0', backgroundColor: '#fff',
  },
  typeBtnActive: { borderColor: '#2E75B6', backgroundColor: '#EBF3FB' },
  typeBtnLabel: { fontSize: 12, color: '#aaa', fontWeight: '600' },
  typeBtnLabelActive: { color: '#2E75B6' },

  addressRow: { flexDirection: 'row', gap: 8, alignItems: 'stretch' },
  addressInput: { flex: 1, marginBottom: 0 },
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

  resolvedBox: {
    flexDirection: 'row', alignItems: 'center', gap: 6,
    backgroundColor: '#EBF3FB', borderRadius: 10, padding: 10, marginTop: 10,
  },
  resolvedText: { fontSize: 12, color: '#2E75B6', fontWeight: '500' },

  submitBtn: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8,
    backgroundColor: '#2E75B6', borderRadius: 14, paddingVertical: 16, marginTop: 24,
  },
  submitBtnDisabled: { backgroundColor: '#B0C8E0' },
  submitBtnText: { fontSize: 16, fontWeight: '700', color: '#fff' },

  // Map picker
  mapContainer: { flex: 1 },
  mapFull: { flex: 1 },
  pin: {
    position: 'absolute', top: '50%', left: '50%',
    marginLeft: -(PIN_HEAD / 2), marginTop: -PIN_HEIGHT,
    alignItems: 'center',
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
