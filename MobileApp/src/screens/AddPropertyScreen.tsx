import { useState } from 'react';
import {
  View, Text, StyleSheet, TextInput, TouchableOpacity,
  ScrollView, ActivityIndicator, KeyboardAvoidingView, Platform,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import TypeSelector from '../components/TypeSelector';
import { PropertyType } from '../lib/advice';
import LocationTabPicker from '../components/LocationTabPicker';
import { apiFetch } from '../lib/api';

interface Props {
  onComplete: () => void;
  onCancel: () => void;
}

export default function AddPropertyScreen({ onComplete, onCancel }: Props) {
  const insets = useSafeAreaInsets();

  const [name, setName] = useState('');
  const [type, setType] = useState<PropertyType>('house');
  const [customTypeName, setCustomTypeName] = useState('');
  const [lat, setLat] = useState<number | null>(null);
  const [lng, setLng] = useState<number | null>(null);
  const [address, setAddress] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!name.trim()) { setFormError('請輸入財產名稱'); return; }
    if (lat === null || lng === null) { setFormError('請選擇財產位置（地址或地圖）'); return; }
    setSubmitting(true);
    setFormError(null);
    try {
      const resp = await apiFetch('/api/properties', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name.trim(), type, latitude: lat, longitude: lng, address,
          custom_type_name: type === 'custom' ? customTypeName.trim() || null : null,
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

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
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
        <Text style={styles.label}>財產名稱</Text>
        <TextInput
          style={styles.input}
          placeholder="例：台北辦公室、愛車"
          value={name}
          onChangeText={setName}
          autoFocus
          returnKeyType="next"
        />

        <Text style={styles.label}>財產類型</Text>
        <TypeSelector
          value={type}
          onChange={setType}
          customTypeName={customTypeName}
          onCustomTypeNameChange={setCustomTypeName}
        />

        <Text style={styles.label}>財產位置</Text>
        <LocationTabPicker
          onLocationChange={(la, ln, addr) => { setLat(la); setLng(ln); setAddress(addr); }}
        />

        {lat !== null && (
          <View style={styles.resolvedBox}>
            <Ionicons name="location" size={14} color="#2E75B6" />
            <Text style={styles.resolvedText}>
              已選座標：{lat.toFixed(5)}, {lng!.toFixed(5)}
            </Text>
          </View>
        )}

        {formError ? (
          <View style={[styles.infoBox, { marginTop: 12 }]}>
            <Ionicons name="alert-circle-outline" size={14} color="#C00000" />
            <Text style={styles.infoBoxTextError}>{formError}</Text>
          </View>
        ) : null}

        <TouchableOpacity
          style={[styles.submitBtn, (submitting || lat === null) && styles.submitBtnDisabled]}
          onPress={handleSubmit}
          disabled={submitting || lat === null}
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
    </KeyboardAvoidingView>
  );
}

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

  input: {
    borderWidth: 1.5, borderColor: '#E0E0E0', borderRadius: 12,
    paddingHorizontal: 14, paddingVertical: 12, fontSize: 15,
    color: '#222', backgroundColor: '#fff',
  },

  infoBox: {
    flexDirection: 'row', alignItems: 'flex-start', gap: 8,
    backgroundColor: '#FFF0F0', padding: 12, borderRadius: 10,
  },
  infoBoxTextError: { fontSize: 13, color: '#C00000', flex: 1 },

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
});
