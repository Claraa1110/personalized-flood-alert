import { View, Text, StyleSheet, TouchableOpacity, Alert } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../context/AuthContext';

type IconName = React.ComponentProps<typeof Ionicons>['name'];

interface SettingRow {
  icon: IconName;
  label: string;
}

const PREF_ROWS: SettingRow[] = [
  { icon: 'notifications-outline', label: '推播通知' },
  { icon: 'volume-high-outline',   label: '警報音效' },
  { icon: 'time-outline',          label: '靜音時段' },
];

export default function SettingsScreen() {
  const { session, signOut } = useAuth();

  const handleSignOut = () => {
    Alert.alert('登出', '確定要登出嗎？', [
      { text: '取消', style: 'cancel' },
      { text: '登出', style: 'destructive', onPress: signOut },
    ]);
  };

  return (
    <View style={styles.container}>
      {/* 帳號資訊 */}
      <Text style={styles.sectionTitle}>帳號</Text>
      <View style={styles.card}>
        <View style={styles.accountRow}>
          <View style={styles.avatarCircle}>
            <Ionicons name="person" size={22} color="#2E75B6" />
          </View>
          <View style={styles.accountInfo}>
            <Text style={styles.accountEmail}>{session?.user?.email ?? '—'}</Text>
            <Text style={styles.accountSub}>已登入</Text>
          </View>
        </View>
      </View>

      {/* 通知偏好 */}
      <Text style={[styles.sectionTitle, { marginTop: 20 }]}>通知偏好</Text>
      <View style={styles.card}>
        {PREF_ROWS.map((row, index) => (
          <View
            key={row.label}
            style={[styles.row, index < PREF_ROWS.length - 1 && styles.rowDivider]}
          >
            <View style={styles.rowLeft}>
              <View style={styles.iconWrap}>
                <Ionicons name={row.icon} size={17} color="#2E75B6" />
              </View>
              <Text style={styles.rowLabel}>{row.label}</Text>
            </View>
            <Text style={styles.devLabel}>開發中</Text>
          </View>
        ))}
      </View>

      {/* 登出 */}
      <TouchableOpacity style={styles.signOutBtn} onPress={handleSignOut}>
        <Ionicons name="log-out-outline" size={18} color="#C00000" />
        <Text style={styles.signOutText}>登出</Text>
      </TouchableOpacity>

      <Text style={styles.version}>版本 1.0.0</Text>
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

  accountRow: { flexDirection: 'row', alignItems: 'center', gap: 14, padding: 16 },
  avatarCircle: {
    width: 44, height: 44, borderRadius: 22,
    backgroundColor: '#EBF3FB', alignItems: 'center', justifyContent: 'center',
  },
  accountInfo: { flex: 1 },
  accountEmail: { fontSize: 15, fontWeight: '600', color: '#1A1A2E' },
  accountSub:   { fontSize: 12, color: '#27AE60', marginTop: 2 },

  row: {
    flexDirection: 'row', alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16, paddingVertical: 14,
  },
  rowDivider: { borderBottomWidth: 1, borderBottomColor: '#F0F0F0' },
  rowLeft:    { flexDirection: 'row', alignItems: 'center', gap: 12 },
  iconWrap: {
    width: 32, height: 32, borderRadius: 8,
    backgroundColor: '#EBF3FB', alignItems: 'center', justifyContent: 'center',
  },
  rowLabel: { fontSize: 15, color: '#1A1A2E' },
  devLabel: { fontSize: 13, color: '#C8C8C8' },

  signOutBtn: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8,
    marginTop: 24, paddingVertical: 14, borderRadius: 14,
    backgroundColor: '#FFF0F0', borderWidth: 1.5, borderColor: '#FFCCCC',
  },
  signOutText: { fontSize: 15, color: '#C00000', fontWeight: '600' },

  version: { textAlign: 'center', fontSize: 12, color: '#ccc', marginTop: 20 },
});
