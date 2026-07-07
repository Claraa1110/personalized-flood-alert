import { useState, useEffect, useCallback } from 'react';
import {
  View, Text, StyleSheet, FlatList,
  ActivityIndicator, TouchableOpacity, RefreshControl,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from '@react-navigation/native';

interface Alert {
  id: string;
  property_id: string;
  level: string;
  message: string;
  created_at: string;
  read_at: string | null;
}

interface PropertyDetail {
  district_name: string | null;
  latitude: number;
  longitude: number;
}

interface ParsedMessage {
  propertyName: string;
  scale: string;
  actualMm: string;
  thresholdMm: string;
  source: string;
}

// 【財產名稱】雨量超過警戒門檻 1H（68.0mm >= 45.0mm）（門檻來源：original）
const MSG_RE = /【(.+?)】雨量超過警戒門檻\s+(\w+)（([\d.]+)mm\s*>=\s*([\d.]+)mm）（門檻來源：(\w+)）/;

function parseMessage(msg: string): ParsedMessage | null {
  const m = msg.match(MSG_RE);
  if (!m) return null;
  return {
    propertyName: m[1],
    scale: m[2],
    actualMm: m[3],
    thresholdMm: m[4],
    source: m[5],
  };
}

export default function AlertScreen() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [propDetails, setPropDetails] = useState<Record<string, PropertyDetail>>({});

  const base = process.env.EXPO_PUBLIC_API_URL;

  const fetchPropertyDetails = async (list: Alert[]) => {
    const uniqueIds = [...new Set(list.map((a) => a.property_id))];
    const results: Record<string, PropertyDetail> = {};
    await Promise.all(
      uniqueIds.map(async (pid) => {
        try {
          const resp = await fetch(`${base}/api/properties/${pid}`);
          if (resp.ok) {
            const p = await resp.json();
            results[pid] = {
              district_name: p.district_name ?? null,
              latitude: p.latitude,
              longitude: p.longitude,
            };
          }
        } catch { /* ignore */ }
      })
    );
    setPropDetails((prev) => ({ ...prev, ...results }));
  };

  const fetchAlerts = async () => {
    try {
      const resp = await fetch(`${base}/api/alerts`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      const list: Alert[] = data.alerts ?? data;
      setAlerts(list);
      setError(null);
      fetchPropertyDetails(list);
    } catch (e: any) {
      setError(e.message ?? '無法載入警報');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => { fetchAlerts(); }, []);

  useFocusEffect(useCallback(() => {
    fetch(`${base}/api/alerts/mark-all-read`, { method: 'POST' }).catch(() => {});
  }, []));

  const onRefresh = () => { setRefreshing(true); fetchAlerts(); };

  const formatTime = (isoStr: string) => {
    const d = new Date(isoStr);
    return d.toLocaleString('zh-TW', {
      month: 'numeric', day: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  };

  const levelColor = (level: string) => {
    if (level === 'warning') return '#C00000';
    if (level === 'notice') return '#E67E22';
    return '#2E75B6';
  };

  const levelIcon = (level: string): React.ComponentProps<typeof Ionicons>['name'] => {
    if (level === 'warning') return 'warning';
    if (level === 'notice') return 'megaphone';
    return 'information-circle';
  };

  const levelText = (level: string) => {
    if (level === 'warning') return '警告';
    if (level === 'notice') return '注意';
    return '通知';
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#2E75B6" />
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.center}>
        <Ionicons name="cloud-offline-outline" size={48} color="#ccc" />
        <Text style={styles.errorText}>{error}</Text>
        <TouchableOpacity style={styles.retryBtn} onPress={fetchAlerts}>
          <Text style={styles.retryText}>重試</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (alerts.length === 0) {
    return (
      <View style={styles.center}>
        <Ionicons name="shield-checkmark-outline" size={56} color="#ccc" />
        <Text style={styles.emptyText}>目前無警報</Text>
        <Text style={styles.emptySubtext}>所有財產雨量正常</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={alerts}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.listContent}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        renderItem={({ item }) => {
          const parsed = parseMessage(item.message);
          const prop = propDetails[item.property_id];
          const color = levelColor(item.level);

          return (
            <View style={[styles.card, { borderLeftColor: color }]}>
              {!item.read_at && <View style={styles.unreadDot} />}

              {/* 頂列：等級 + 時間 */}
              <View style={styles.cardTop}>
                <View style={[styles.levelBadge, { backgroundColor: color + '18' }]}>
                  <Ionicons name={levelIcon(item.level)} size={13} color={color} />
                  <Text style={[styles.levelText, { color }]}>{levelText(item.level)}</Text>
                </View>
                <Text style={styles.timeText}>{formatTime(item.created_at)}</Text>
              </View>

              {/* 財產名稱 */}
              <Text style={styles.propName}>
                {parsed?.propertyName ?? '—'}
              </Text>

              {/* 縣市地區 */}
              <View style={styles.districtRow}>
                <Ionicons name="location-outline" size={13} color="#999" />
                <Text style={styles.districtText}>
                  {prop ? (prop.district_name ?? '無地區資料') : '—'}
                </Text>
              </View>

              <View style={styles.divider} />

              {/* 雨量資訊 */}
              {parsed ? (
                <View style={styles.rainfallSection}>
                  <View style={styles.rainfallRow}>
                    <View style={styles.scaleBadge}>
                      <Text style={styles.scaleText}>{parsed.scale}</Text>
                    </View>
                    <Text style={styles.rainfallMain}>
                      雨量{' '}
                      <Text style={[styles.rainfallValue, { color }]}>
                        {parsed.actualMm} mm
                      </Text>
                    </Text>
                    <Text style={styles.rainfallSub}>門檻 {parsed.thresholdMm} mm</Text>
                  </View>
                  <View style={[
                    styles.sourceBadge,
                    { backgroundColor: parsed.source === 'corrected' ? '#EBF3FB' : '#F5F5F5' },
                  ]}>
                    <Text style={[
                      styles.sourceText,
                      { color: parsed.source === 'corrected' ? '#2E75B6' : '#888' },
                    ]}>
                      {parsed.source === 'corrected' ? '校正後門檻' : 'WRA 原始門檻'}
                    </Text>
                  </View>
                </View>
              ) : (
                <Text style={styles.rawMessage}>{item.message}</Text>
              )}
            </View>
          );
        }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F0F4F8',
  },
  listContent: {
    padding: 16,
    gap: 12,
    paddingBottom: 32,
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 10,
    backgroundColor: '#F0F4F8',
  },
  emptyText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#aaa',
    marginTop: 8,
  },
  emptySubtext: {
    fontSize: 14,
    color: '#bbb',
  },
  errorText: {
    color: '#C00000',
    fontSize: 15,
    marginTop: 8,
  },
  retryBtn: {
    backgroundColor: '#2E75B6',
    paddingHorizontal: 28,
    paddingVertical: 10,
    borderRadius: 20,
    marginTop: 4,
  },
  retryText: {
    color: '#fff',
    fontWeight: '600',
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 16,
    borderLeftWidth: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.07,
    shadowRadius: 6,
    elevation: 3,
  },
  unreadDot: {
    position: 'absolute',
    top: 14,
    right: 14,
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#C00000',
  },
  cardTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  levelBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 20,
  },
  levelText: {
    fontSize: 12,
    fontWeight: '700',
  },
  timeText: {
    color: '#aaa',
    fontSize: 12,
  },
  propName: {
    fontSize: 18,
    fontWeight: '700',
    color: '#1A1A2E',
    marginBottom: 4,
  },
  districtRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginBottom: 12,
  },
  districtText: {
    fontSize: 13,
    color: '#888',
  },
  divider: {
    height: 1,
    backgroundColor: '#F0F0F0',
    marginBottom: 12,
  },
  rainfallSection: {
    gap: 8,
  },
  rainfallRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  scaleBadge: {
    backgroundColor: '#1A1A2E',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 8,
  },
  scaleText: {
    color: '#fff',
    fontWeight: '700',
    fontSize: 13,
  },
  rainfallMain: {
    fontSize: 14,
    color: '#444',
    flex: 1,
  },
  rainfallValue: {
    fontWeight: '700',
    fontSize: 15,
  },
  rainfallSub: {
    fontSize: 13,
    color: '#888',
  },
  sourceBadge: {
    alignSelf: 'flex-start',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 8,
  },
  sourceText: {
    fontSize: 12,
    fontWeight: '600',
  },
  rawMessage: {
    fontSize: 13,
    color: '#666',
    lineHeight: 18,
  },
});
