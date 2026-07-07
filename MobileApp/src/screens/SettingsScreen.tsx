import { View, Text, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

type IconName = React.ComponentProps<typeof Ionicons>['name'];

interface SettingRow {
  icon: IconName;
  label: string;
}

const SECTIONS: { title: string; rows: SettingRow[] }[] = [
  {
    title: '帳號',
    rows: [
      { icon: 'person-outline', label: '使用者' },
      { icon: 'mail-outline', label: '電子郵件' },
    ],
  },
  {
    title: '通知偏好',
    rows: [
      { icon: 'notifications-outline', label: '推播通知' },
      { icon: 'volume-high-outline', label: '警報音效' },
      { icon: 'time-outline', label: '靜音時段' },
    ],
  },
];

export default function SettingsScreen() {
  return (
    <View style={styles.container}>
      {SECTIONS.map((section) => (
        <View key={section.title} style={styles.section}>
          <Text style={styles.sectionTitle}>{section.title}</Text>
          <View style={styles.card}>
            {section.rows.map((row, index) => (
              <View
                key={row.label}
                style={[styles.row, index < section.rows.length - 1 && styles.rowDivider]}
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
        </View>
      ))}
      <Text style={styles.version}>版本 1.0.0 · 開發中</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F0F4F8',
    padding: 16,
  },
  section: {
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 12,
    color: '#888',
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    paddingHorizontal: 4,
    marginBottom: 6,
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: 16,
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 6,
    elevation: 3,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 14,
  },
  rowDivider: {
    borderBottomWidth: 1,
    borderBottomColor: '#F0F0F0',
  },
  rowLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  iconWrap: {
    width: 32,
    height: 32,
    borderRadius: 8,
    backgroundColor: '#EBF3FB',
    alignItems: 'center',
    justifyContent: 'center',
  },
  rowLabel: {
    fontSize: 15,
    color: '#1A1A2E',
  },
  devLabel: {
    fontSize: 13,
    color: '#C8C8C8',
  },
  version: {
    textAlign: 'center',
    fontSize: 12,
    color: '#ccc',
    marginTop: 8,
  },
});
