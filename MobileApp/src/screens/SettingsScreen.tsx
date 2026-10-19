import { useState, useEffect } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity,
  Switch, ActivityIndicator, Linking, Alert, Modal,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { apiFetch, extractErrorMessage } from '../lib/api';
import { clearPropertyCache } from '../lib/propertyCache';
import AboutScreen from './AboutScreen';

type IconName = React.ComponentProps<typeof Ionicons>['name'];

function PrefRow({
  icon, label, value, onToggle, isLast = false, loading,
}: {
  icon: IconName; label: string; value: boolean;
  onToggle: (v: boolean) => void; isLast?: boolean; loading: boolean;
}) {
  return (
    <View style={[styles.row, !isLast && styles.rowDivider]}>
      <View style={styles.rowLeft}>
        <View style={styles.iconWrap}>
          <Ionicons name={icon} size={17} color="#2E75B6" />
        </View>
        <Text style={styles.rowLabel}>{label}</Text>
      </View>
      {loading
        ? <ActivityIndicator size="small" color="#2E75B6" />
        : <Switch
            value={value}
            onValueChange={onToggle}
            trackColor={{ false: '#E0E0E0', true: '#2E75B6' }}
            thumbColor="#fff"
          />
      }
    </View>
  );
}

function LinkRow({
  icon, label, onPress, isLast = false,
}: {
  icon: IconName; label: string; onPress: () => void; isLast?: boolean;
}) {
  return (
    <TouchableOpacity
      style={[styles.row, !isLast && styles.rowDivider]}
      onPress={onPress}
      activeOpacity={0.7}
    >
      <View style={styles.rowLeft}>
        <View style={styles.iconWrap}>
          <Ionicons name={icon} size={17} color="#2E75B6" />
        </View>
        <Text style={styles.rowLabel}>{label}</Text>
      </View>
      <Ionicons name="chevron-forward" size={16} color="#ccc" />
    </TouchableOpacity>
  );
}

export default function SettingsScreen() {
  const [notifyEnabled, setNotifyEnabled] = useState(true);
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(false);
  const [aboutVisible, setAboutVisible] = useState(false);

  useEffect(() => {
    apiFetch('/api/notification-settings')
      .then(r => r.json())
      .then(data => {
        setNotifyEnabled(data.notify_enabled);
        setSoundEnabled(data.sound_enabled);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const saveSettings = (notify: boolean, sound: boolean) => {
    apiFetch('/api/notification-settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ notify_enabled: notify, sound_enabled: sound }),
    }).catch(() => {});
  };

  const handleNotifyToggle = (value: boolean) => {
    setNotifyEnabled(value);
    saveSettings(value, soundEnabled);
  };

  const handleSoundToggle = (value: boolean) => {
    setSoundEnabled(value);
    saveSettings(notifyEnabled, value);
  };

  const handleDeleteAllData = () => {
    Alert.alert(
      '刪除所有資料',
      '此操作將永久清除此裝置的所有財產、警報紀錄與設定，且無法復原。\n\n確定要繼續嗎？',
      [
        { text: '取消', style: 'cancel' },
        {
          text: '確定刪除',
          style: 'destructive',
          onPress: async () => {
            setDeleting(true);
            try {
              const resp = await apiFetch('/api/me/data', { method: 'DELETE' });
              if (!resp.ok) {
                const err = await resp.json().catch(() => ({}));
                throw new Error(extractErrorMessage(err, `HTTP ${resp.status}`));
              }
              clearPropertyCache();
              Alert.alert('已完成', '所有資料已清除，App 已回到初始狀態。');
            } catch (e: any) {
              Alert.alert('刪除失敗', e.message ?? '請稍後再試');
            } finally {
              setDeleting(false);
            }
          },
        },
      ]
    );
  };

  return (
    <View style={styles.container}>
      {/* ── 通知偏好 ── */}
      <Text style={styles.sectionTitle}>通知偏好</Text>
      <View style={styles.card}>
        <PrefRow
          icon="notifications-outline"
          label="推播通知"
          value={notifyEnabled}
          onToggle={handleNotifyToggle}
          loading={loading}
        />
        <PrefRow
          icon="volume-high-outline"
          label="警報音效"
          value={soundEnabled}
          onToggle={handleSoundToggle}
          isLast
          loading={loading}
        />
      </View>

      {/* ── 關於 ── */}
      <Text style={[styles.sectionTitle, { marginTop: 20 }]}>關於</Text>
      <View style={styles.card}>
        <LinkRow
          icon="information-circle-outline"
          label="關於本 App"
          onPress={() => setAboutVisible(true)}
        />
        <LinkRow
          icon="document-text-outline"
          label="隱私權政策"
          onPress={() => Linking.openURL('https://ff-weathered-paper-9628.fly.dev/privacy')}
          isLast
        />
      </View>

      {/* ── 資料 ── */}
      <Text style={[styles.sectionTitle, { marginTop: 20 }]}>資料</Text>
      <View style={styles.dangerCard}>
        <TouchableOpacity
          style={styles.row}
          onPress={handleDeleteAllData}
          disabled={deleting}
          activeOpacity={0.75}
        >
          <View style={styles.rowLeft}>
            <View style={styles.iconWrapDanger}>
              <Ionicons name="trash-outline" size={17} color="#C00000" />
            </View>
            <View style={styles.dangerTextWrap}>
              <Text style={styles.dangerRowLabel}>刪除所有資料</Text>
              <Text style={styles.dangerRowSub}>清除此裝置的所有財產與設定</Text>
            </View>
          </View>
          {deleting
            ? <ActivityIndicator size="small" color="#C00000" />
            : <Ionicons name="chevron-forward" size={16} color="#ccc" />}
        </TouchableOpacity>
      </View>

      <Text style={styles.version}>版本 1.0.0</Text>

      {/* ── 關於本 App Modal ── */}
      <Modal
        visible={aboutVisible}
        animationType="slide"
        onRequestClose={() => setAboutVisible(false)}
      >
        <AboutScreen onClose={() => setAboutVisible(false)} />
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F0F4F8', padding: 16 },

  sectionTitle: {
    fontSize: 12, color: '#888', fontWeight: '600',
    textTransform: 'uppercase', letterSpacing: 0.5,
    paddingHorizontal: 4, marginBottom: 6,
  },
  card: {
    backgroundColor: '#fff', borderRadius: 16, overflow: 'hidden',
    shadowColor: '#000', shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06, shadowRadius: 6, elevation: 3,
  },
  dangerCard: {
    backgroundColor: '#fff', borderRadius: 16, overflow: 'hidden',
    borderWidth: 1, borderColor: '#FFDDDD',
    shadowColor: '#C00000', shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06, shadowRadius: 6, elevation: 3,
  },

  row: {
    flexDirection: 'row', alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16, paddingVertical: 14,
  },
  rowDivider: { borderBottomWidth: 1, borderBottomColor: '#F0F0F0' },
  rowLeft: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  iconWrap: {
    width: 32, height: 32, borderRadius: 8,
    backgroundColor: '#EBF3FB', alignItems: 'center', justifyContent: 'center',
  },
  iconWrapDanger: {
    width: 32, height: 32, borderRadius: 8,
    backgroundColor: '#FFF0F0', alignItems: 'center', justifyContent: 'center',
  },
  rowLabel: { fontSize: 15, color: '#1A1A2E' },

  dangerTextWrap: { gap: 2 },
  dangerRowLabel: { fontSize: 15, color: '#C00000', fontWeight: '600' },
  dangerRowSub: { fontSize: 12, color: '#aaa' },

  version: { textAlign: 'center', fontSize: 12, color: '#ccc', marginTop: 20 },
});
