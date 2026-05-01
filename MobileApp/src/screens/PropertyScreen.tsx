import { useState } from 'react';
import { View, TouchableOpacity, Text, StyleSheet, ActivityIndicator } from 'react-native';
import MapView from 'react-native-maps';

interface RainfallResult {
  station_name: string;
  distance_km: number;
  rainfall_mm: number;
  observed_at: string;
}

export default function PropertyScreen() {
  const [viewMode, setViewMode] = useState<'map' | 'list'>('map');
  const [loading, setLoading] = useState(false);
  const [rainfall, setRainfall] = useState<RainfallResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function testRainfall() {
    setLoading(true);
    setError(null);
    setRainfall(null);
    try {
      const base = process.env.EXPO_PUBLIC_API_URL;
      const resp = await fetch(`${base}/api/test-rainfall?lat=25.04&lng=121.51`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data: RainfallResult = await resp.json();
      setRainfall(data);
    } catch (e: any) {
      setError(e.message ?? '連線失敗');
    } finally {
      setLoading(false);
    }
  }

  return (
    <View style={{ flex: 1 }}>
      <View style={styles.toggleRow}>
        <TouchableOpacity
          style={[styles.toggleBtn, viewMode === 'map' && styles.active]}
          onPress={() => setViewMode('map')}
        >
          <Text>🗺 地圖</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.toggleBtn, viewMode === 'list' && styles.active]}
          onPress={() => setViewMode('list')}
        >
          <Text>📋 列表</Text>
        </TouchableOpacity>
      </View>

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
            {error && (
              <View style={styles.resultBox}>
                <Text style={[styles.resultText, { color: 'red' }]}>{error}</Text>
              </View>
            )}
          </View>
        </View>
      )}

      {viewMode === 'list' && (
        <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
          <Text>財產列表（待完成）</Text>
        </View>
      )}
    </View>
  );
}

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
});
