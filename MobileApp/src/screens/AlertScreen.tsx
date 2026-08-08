import { useState, useEffect, useCallback } from 'react';
import { updateBadgeCount } from '../lib/notifications';
import {
  View, Text, StyleSheet, FlatList,
  ActivityIndicator, TouchableOpacity, RefreshControl,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from '@react-navigation/native';
import { apiFetch } from '../lib/api';
import { getAdviceText } from '../lib/advice';

// ─── Types ────────────────────────────────────────────────────────────────────

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
  type: string | null;
  custom_type_name: string | null;
}

interface ParsedMessage {
  propertyName: string;
  alertLevel: string;
  scale: string;
  actualMm: string;
  thresholdMm: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

// 【財產名稱】達一級警戒 3H 雨量 52.5mm（已達警戒值 45.0mm）
const MSG_RE = /【(.+?)】達(一級警戒|二級預警)\s+(\w+)\s+雨量\s+([\d.]+)mm（已達(?:警戒|預警)值\s+([\d.]+)mm）/;


// ─── Helpers ──────────────────────────────────────────────────────────────────

function parseMessage(msg: string): ParsedMessage | null {
  const m = msg.match(MSG_RE);
  if (!m) return null;
  return {
    propertyName: m[1],
    alertLevel: m[2],
    scale: m[3],
    actualMm: m[4],
    thresholdMm: m[5],
  };
}

// DB 回傳無時區的 UTC 字串，補 'Z' 讓 JS 正確解讀為 UTC
function parseUTC(isoStr: string): Date {
  if (!isoStr.endsWith('Z') && !isoStr.includes('+')) return new Date(isoStr + 'Z');
  return new Date(isoStr);
}

function formatTime(isoStr: string) {
  return parseUTC(isoStr).toLocaleString('zh-TW', {
    timeZone: 'Asia/Taipei',
    month: 'numeric', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function AlertScreen() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [propDetails, setPropDetails] = useState<Record<string, PropertyDetail>>({});
  const [lastUpdatedMin, setLastUpdatedMin] = useState<number | null>(null);

  const fetchPropertyDetails = async (list: Alert[]) => {
    const uniqueIds = [...new Set(list.map((a) => a.property_id))];
    const results: Record<string, PropertyDetail> = {};
    await Promise.all(
      uniqueIds.map(async (pid) => {
        try {
          const resp = await apiFetch(`/api/properties/${pid}`);
          if (resp.ok) {
            const p = await resp.json();
            results[pid] = {
              district_name: p.district_name ?? null,
              type: p.type ?? null,
              custom_type_name: p.custom_type_name ?? null,
            };
          }
        } catch { /* ignore */ }
      })
    );
    setPropDetails((prev) => ({ ...prev, ...results }));
  };

  const fetchAlerts = async () => {
    try {
      const [alertResp, schedulerResp] = await Promise.all([
        apiFetch('/api/alerts'),
        apiFetch('/health/scheduler'),
      ]);

      if (!alertResp.ok) throw new Error(`HTTP ${alertResp.status}`);
      const data = await alertResp.json();
      const all: Alert[] = data.alerts ?? data;

      setAlerts(all);
      setError(null);
      fetchPropertyDetails(all);

      if (schedulerResp.ok) {
        const sched = await schedulerResp.json();
        setLastUpdatedMin(sched.minutes_since_last_update ?? null);
      }
    } catch (e: any) {
      setError(e.message ?? '無法載入警報');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => { fetchAlerts(); }, []);

  useFocusEffect(useCallback(() => {
    apiFetch('/api/alerts/mark-all-read', { method: 'POST' })
      .then(() => updateBadgeCount())
      .catch(() => {});
  }, []));

  const onRefresh = () => { setRefreshing(true); fetchAlerts(); };

  // ── States ───────────────────────────────────────────────────────────────────

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

  const updateLabel = lastUpdatedMin === null
    ? null
    : lastUpdatedMin < 1
      ? '剛剛更新'
      : `${Math.round(lastUpdatedMin)} 分鐘前更新`;

  if (alerts.length === 0) {
    return (
      <View style={styles.container}>
        {updateLabel && (
          <View style={styles.updateBar}>
            <Ionicons name="time-outline" size={13} color="#aaa" />
            <Text style={styles.updateText}>雨量資料 {updateLabel}</Text>
          </View>
        )}
        <View style={styles.center}>
          <Ionicons name="shield-checkmark-outline" size={56} color="#ccc" />
          <Text style={styles.emptyText}>尚無警報記錄</Text>
          <Text style={styles.emptySubtext}>所有財產雨量正常</Text>
        </View>
      </View>
    );
  }

  // ── Render ────────────────────────────────────────────────────────────────────

  return (
    <View style={styles.container}>
      {updateLabel && (
        <View style={styles.updateBar}>
          <Ionicons name="time-outline" size={13} color="#aaa" />
          <Text style={styles.updateText}>雨量資料 {updateLabel}</Text>
        </View>
      )}
      <FlatList
        data={alerts}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.listContent}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        renderItem={({ item }) => {
          const parsed = parseMessage(item.message);
          const prop = propDetails[item.property_id];
          const typeKey = prop?.type ?? 'other';
          const isLevel1 = item.level === 'level1';
          const accentColor = isLevel1 ? '#C00000' : '#E67E22';
          const rawLevel = parsed?.alertLevel ?? (isLevel1 ? '一級警戒' : '二級預警');
          const levelLabel = rawLevel === '一級警戒' ? '警戒' : '注意';
          const levelKey = isLevel1 ? 'level1' : 'level2';
          const advice = getAdviceText(levelKey, typeKey);
          const adviceBg = isLevel1 ? '#FFF0F0' : '#FFF5EC';
          const adviceBorder = isLevel1 ? '#FFCCCC' : '#FFDDB8';
          const adviceTextColor = isLevel1 ? '#8B0000' : '#7D4000';

          return (
            <View style={[styles.card, { borderLeftColor: accentColor }]}>
              {/* 未讀紅點 */}
              {!item.read_at && <View style={styles.unreadDot} />}

              {/* 頂列：等級 + 財產名稱 / 時間 */}
              <View style={styles.cardTop}>
                <View style={styles.titleRow}>
                  <Ionicons name="warning" size={15} color={accentColor} />
                  <Text style={[styles.levelLabel, { color: accentColor }]}>
                    {levelLabel}
                  </Text>
                  <Text style={styles.dot}>·</Text>
                  <Text style={styles.propName} numberOfLines={1}>
                    {parsed?.propertyName ?? '—'}
                  </Text>
                </View>
                <Text style={styles.timeText}>{formatTime(item.created_at)}</Text>
              </View>

              {/* 地區 */}
              <View style={styles.districtRow}>
                <Text style={styles.districtPin}>📍</Text>
                <Text style={styles.districtText}>
                  {prop ? (prop.district_name ?? '無地區資料') : '—'}
                </Text>
              </View>

              {/* 行動建議 */}
              <View style={[styles.adviceBox, { backgroundColor: adviceBg, borderColor: adviceBorder }]}>
                <Text style={styles.adviceIcon}>⚠️</Text>
                <Text style={[styles.adviceText, { color: adviceTextColor }]}>{advice}</Text>
              </View>
            </View>
          );
        }}
      />
    </View>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F0F4F8' },
  listContent: { padding: 16, gap: 12, paddingBottom: 32 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', gap: 10, backgroundColor: '#F0F4F8' },
  emptyText: { fontSize: 18, fontWeight: '600', color: '#aaa', marginTop: 8 },
  emptySubtext: { fontSize: 14, color: '#bbb' },
  errorText: { color: '#C00000', fontSize: 15, marginTop: 8 },
  retryBtn: { backgroundColor: '#2E75B6', paddingHorizontal: 28, paddingVertical: 10, borderRadius: 20, marginTop: 4 },
  retryText: { color: '#fff', fontWeight: '600' },

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
    gap: 8,
  },
  unreadDot: {
    position: 'absolute', top: 14, right: 14,
    width: 8, height: 8, borderRadius: 4,
    backgroundColor: '#C00000',
  },

  cardTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    flex: 1,
    marginRight: 12,
  },
  levelLabel: { fontSize: 13, fontWeight: '700' },
  dot: { fontSize: 13, color: '#ccc' },
  propName: { fontSize: 15, fontWeight: '700', color: '#1A1A2E', flex: 1 },
  timeText: { fontSize: 12, color: '#aaa', flexShrink: 0 },

  districtRow: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  districtPin: { fontSize: 13 },
  districtText: { fontSize: 13, color: '#666' },

  rainfallSentence: { fontSize: 14, color: '#444', lineHeight: 20 },
  rainfallScaleLabel: { fontWeight: '600', color: '#333' },
  rainfallValue: { fontWeight: '700', fontSize: 15 },

  adviceBox: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    backgroundColor: '#FFF0F0',
    borderRadius: 10,
    padding: 10,
    borderWidth: 1,
    borderColor: '#FFCCCC',
    marginTop: 2,
  },
  adviceIcon: { fontSize: 14, lineHeight: 20 },
  adviceText: { fontSize: 13, color: '#8B0000', lineHeight: 19, flex: 1, fontWeight: '500' },

  updateBar: {
    flexDirection: 'row', alignItems: 'center', gap: 5,
    paddingHorizontal: 16, paddingVertical: 8,
    backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: '#EAEAEA',
  },
  updateText: { fontSize: 12, color: '#aaa' },
});
