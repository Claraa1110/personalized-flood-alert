import { useState } from 'react';
import { View, TouchableOpacity, Text, StyleSheet } from 'react-native';
import MapView from 'react-native-maps';

export default function PropertyScreen() {
  const [viewMode, setViewMode] = useState<'map' | 'list'>('map');

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
        <MapView
          style={{ flex: 1 }}
          initialRegion={{
            latitude: 25.0339,
            longitude: 121.5645,
            latitudeDelta: 0.05,
            longitudeDelta: 0.05,
          }}
        />
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
});
