import { useState, useCallback } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity,
  ActivityIndicator, ScrollView, RefreshControl,
} from 'react-native';
import { useFocusEffect, useNavigation } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';

// ─── Interfaces ───────────────────────────────────────────────────────────────

interface Alert {
  id: string;
  property_id: string;
  level: string;
  message: string;
  created_at: string;
  read_at: string | null;
}

interface Property {
  id: string;
  name: string;
  type: string;
  latitude: number;
  longitude: number;
  district_name: string | null;
}

interface PropertyRisk {
  property: Property;
  riskPct: number;
  riskLevel: 'safe' | 'notice' | 'warning' | 'critical';
  topScale: string | null;
  topMm: number | null;
  topThreshold: number | null;
  hasData: boolean;
}

interface PropertyForecast {
  property: Property;
  districtName: string | null;
  maxPop6h: number;
}

// ─── Pure helpers ─────────────────────────────────────────────────────────────

function buildRisk(property: Property, rf: any, thr: any): PropertyRisk {
  const empty: PropertyRisk = {
    property, riskPct: 0, riskLevel: 'safe',
    topScale: null, topMm: null, topThreshold: null, hasData: false,
  };
  if (!rf || !thr) return empty;

  const candidates: { scale: string; mm: number; threshold: number; pct: number }[] = [];
  if (rf.rainfall_1hr_mm != null && thr.threshold_1h) {
    candidates.push({ scale: '1H', mm: rf.rainfall_1hr_mm, threshold: thr.threshold_1h, pct: rf.rainfall_1hr_mm / thr.threshold_1h * 100 });
  }
  if (rf.rainfall_3hr_mm != null && thr.threshold_3h) {
    candidates.push({ scale: '3H', mm: rf.rainfall_3hr_mm, threshold: thr.threshold_3h, pct: rf.rainfall_3hr_mm / thr.threshold_3h * 100 });
  }
  if (candidates.length === 0) return empty;

  const top = candidates.reduce((a, b) => a.pct > b.pct ? a : b);
  const pct = top.pct;
  const riskLevel = pct >= 100 ? 'critical' : pct >= 80 ? 'warning' : pct >= 50 ? 'notice' : 'safe';

  return { property, riskPct: pct, riskLevel, topScale: top.scale, topMm: top.mm, topThreshold: top.threshold, hasData: true };
}

function getRiskColor(level: PropertyRisk['riskLevel']): string {
  return { safe: '#27AE60', notice: '#F1C40F', warning: '#E67E22', critical: '#C00000' }[level];
}

function getRiskLabel(level: PropertyRisk['riskLevel']): string {
  return { safe: '安全', notice: '注意', warning: '警戒', critical: '超過門檻' }[level];
}

function getTypeIcon(type: string): React.ComponentProps<typeof Ionicons>['name'] {
  if (type === 'house') return 'home-outline';
  if (type === 'car') return 'car-outline';
  if (type === 'warehouse') return 'business-outline';
  return 'cube-outline';
}

function getForecastAppearance(pop: number): { bg: string; accent: string; icon: string; hint: string | null } {
  if (pop < 20) return { bg: '#EEF3F8', accent: '#7B9AB5', icon: '☀️', hint: '近期無明顯降雨' };
  if (pop < 50) return { bg: '#E3EEF9', accent: '#2E75B6', icon: '🌦️', hint: null };
  if (pop < 70) return { bg: '#C8DCF0', accent: '#1A5C9C', icon: '🌧️', hint: null };
  return { bg: '#A8C4E0', accent: '#0D3A6E', icon: '⛈️', hint: '建議留意' };
}

function getAdvice(level: PropertyRisk['riskLevel'], type: string): string {
  if (level === 'safe') return '持續監測中，無需行動';
  if (level === 'notice') return '留意天氣變化，確認排水孔暢通';
  if (level === 'warning') {
    if (type === 'house') return '貴重物品移至高樓層，確認一樓門窗防水';
    if (type === 'car') return '將車輛開往高處停放';
    if (type === 'warehouse') return '墊高庫存，確認防水措施';
    return '移動重要物品至高處';
  }
  if (type === 'house') return '緊急：一樓人員注意安全，切勿進入地下室';
  if (type === 'car') return '緊急：立即移車，遠離低窪停車區';
  if (type === 'warehouse') return '緊急：關閉電源總開關，人員撤離';
  return '緊急：遠離淹水區域，注意人身安全';
}

// ─── RiskCard ─────────────────────────────────────────────────────────────────

function RiskCard({ risk, onPress }: { risk: PropertyRisk; onPress: () => void }) {
  const color = getRiskColor(risk.riskLevel);
  const label = getRiskLabel(risk.riskLevel);
  const icon = getTypeIcon(risk.property.type);
  const advice = getAdvice(risk.riskLevel, risk.property.type);

  return (
    <TouchableOpacity
      style={[styles.riskCard, { borderLeftColor: color }]}
      onPress={onPress}
      activeOpacity={0.85}
    >
      <View style={styles.riskCardTop}>
        <Ionicons name={icon} size={14} color={color} />
        <Text style={styles.riskPropName} numberOfLines={1}>
          {risk.property.name}
          {risk.property.district_name ? ` · ${risk.property.district_name}` : ''}
        </Text>
        <View style={[styles.riskBadge, { backgroundColor: color + '22' }]}>
          <Text style={[styles.riskPctText, { color }]}>{Math.round(risk.riskPct)}%</Text>
          <Text style={[styles.riskLevelText, { color }]}>{label}</Text>
        </View>
      </View>

      {risk.hasData && risk.topScale != null && (
        <>
          <View style={styles.riskDivider} />
          <Text style={styles.riskRainfallText}>
            {risk.topScale} 雨量 {risk.topMm?.toFixed(1)}mm / 門檻 {risk.topThreshold?.toFixed(0)}mm
          </Text>
          <View style={styles.riskAdviceRow}>
            <Ionicons name="bulb-outline" size={12} color="#E67E22" />
            <Text style={styles.riskAdviceText}>{advice}</Text>
          </View>
        </>
      )}
    </TouchableOpacity>
  );
}

// ─── SVG 元件（保留備用，之後財產詳情頁使用） ─────────────────────────────────
// import { Dimensions } from 'react-native';
// import Svg, { Circle, Line, Polyline, Rect, Text as SvgText } from 'react-native-svg';
// import * as Location from 'expo-location';
//
// const SCREEN_W = Dimensions.get('window').width;
//
// function WeatherIcon({ mm }: { mm: number }) { ... }
// function RainfallLineChart({ series, threshold }: { ... }) { ... }

// ─── HomeScreen ───────────────────────────────────────────────────────────────

export default function HomeScreen() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [propertyRisks, setPropertyRisks] = useState<PropertyRisk[]>([]);
  const [forecastList, setForecastList] = useState<PropertyForecast[]>([]);
  const [loading, setLoading] = useState(true);
  const [risksLoading, setRisksLoading] = useState(true);
  const [forecastLoading, setForecastLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const navigation = useNavigation<any>();
  const base = process.env.EXPO_PUBLIC_API_URL;

  const fetchPropertyRisks = async (properties: Property[]): Promise<PropertyRisk[]> => {
    const results = await Promise.all(
      properties.map(async (p) => {
        const [rfRes, thrRes] = await Promise.allSettled([
          fetch(`${base}/api/rainfall?lat=${p.latitude}&lng=${p.longitude}`),
          fetch(`${base}/api/threshold?lat=${p.latitude}&lng=${p.longitude}`),
        ]);
        let rf: any = null;
        if (rfRes.status === 'fulfilled' && rfRes.value.ok) rf = await rfRes.value.json();
        let thr: any = null;
        if (thrRes.status === 'fulfilled' && thrRes.value.ok) {
          const t = await thrRes.value.json();
          if (!t.error) thr = t;
        }
        return buildRisk(p, rf, thr);
      })
    );
    return results.sort((a, b) => b.riskPct - a.riskPct);
  };

  const fetchForecasts = async (properties: Property[]): Promise<void> => {
    const results = await Promise.all(
      properties.map(async (p) => {
        try {
          const resp = await fetch(`${base}/api/forecast?lat=${p.latitude}&lng=${p.longitude}`);
          if (!resp.ok) return null;
          const data = await resp.json();
          if (data.max_pop_6h === null) return null;
          return { property: p, districtName: data.district_name as string | null, maxPop6h: data.max_pop_6h as number };
        } catch {
          return null;
        }
      })
    );
    const list = results
      .filter((r): r is PropertyForecast => r !== null && r.maxPop6h >= 30)
      .sort((a, b) => b.maxPop6h - a.maxPop6h);
    setForecastList(list);
    setForecastLoading(false);
  };

  const fetchData = async () => {
    const [alertResult, propertiesResult] = await Promise.allSettled([
      fetch(`${base}/api/alerts`),
      fetch(`${base}/api/properties`),
    ]);

    if (alertResult.status === 'fulfilled' && alertResult.value.ok) {
      const data = await alertResult.value.json();
      setAlerts(data.alerts ?? data);
    }

    setLoading(false);

    if (propertiesResult.status === 'fulfilled' && propertiesResult.value.ok) {
      const props: Property[] = await propertiesResult.value.json();
      const [risks] = await Promise.all([
        fetchPropertyRisks(props),
        fetchForecasts(props),
      ]);
      setPropertyRisks(risks);
    } else {
      setForecastLoading(false);
    }
    setRisksLoading(false);
    setRefreshing(false);
  };

  useFocusEffect(useCallback(() => {
    setLoading(true);
    setRisksLoading(true);
    setForecastLoading(true);
    fetchData();
  }, []));

  const onRefresh = () => { setRefreshing(true); setForecastLoading(true); fetchData(); };

  const renderRisksSection = () => {
    if (risksLoading) {
      return (
        <View style={styles.risksLoading}>
          <ActivityIndicator size="small" color="#2E75B6" />
          <Text style={styles.risksLoadingText}>計算財產風險中…</Text>
        </View>
      );
    }
    if (propertyRisks.length === 0) return null;

    const notSafe = propertyRisks.filter(r => r.riskLevel !== 'safe');
    const safe = propertyRisks.filter(r => r.riskLevel === 'safe');

    if (notSafe.length === 0) {
      const lastAlertDate = alerts.length > 0
        ? new Date(alerts[0].created_at).toLocaleDateString('zh-TW', { month: 'numeric', day: 'numeric' })
        : null;
      return (
        <View style={styles.allSafeWrap}>
          <View style={styles.allSafeRow}>
            <Ionicons name="shield-checkmark-outline" size={15} color="#27AE60" />
            <Text style={styles.allSafeText}>{propertyRisks.length} 個財產都在安全範圍</Text>
          </View>
          <Text style={styles.lastAlertText}>
            {lastAlertDate ? `最近一次警報：${lastAlertDate}` : '尚無警報記錄'}
          </Text>
        </View>
      );
    }

    const safeToShow = safe.slice(0, 2);
    const safeCollapsed = safe.slice(2);

    return (
      <View style={styles.risksGroup}>
        {notSafe.map(r => (
          <RiskCard key={r.property.id} risk={r} onPress={() => navigation.navigate('列表')} />
        ))}
        {safeToShow.map(r => (
          <RiskCard key={r.property.id} risk={r} onPress={() => navigation.navigate('列表')} />
        ))}
        {safeCollapsed.length > 0 && (
          <View style={styles.collapsedRow}>
            <Ionicons name="shield-checkmark-outline" size={13} color="#27AE60" />
            <Text style={styles.collapsedText}>
              其他 {safeCollapsed.length} 個財產都在安全範圍
            </Text>
          </View>
        )}
      </View>
    );
  };

  const renderForecastSection = () => {
    if (forecastLoading) {
      return (
        <View style={styles.risksLoading}>
          <ActivityIndicator size="small" color="#2E75B6" />
          <Text style={styles.risksLoadingText}>查詢降雨預報中…</Text>
        </View>
      );
    }
    if (forecastList.length === 0) {
      return (
        <View style={styles.forecastCard}>
          <Text style={styles.forecastNoData}>暫無預報資料</Text>
        </View>
      );
    }
    return (
      <View style={styles.forecastGroup}>
        <Text style={styles.forecastIntro}>以下財產所在地未來 6 小時可能降雨：</Text>
        {forecastList.map((f) => {
          const { bg, accent, icon, hint } = getForecastAppearance(f.maxPop6h);
          const district = f.districtName ?? f.property.district_name ?? '';
          return (
            <View key={f.property.id} style={[styles.forecastCard, { backgroundColor: bg }]}>
              <Text style={styles.forecastIcon}>{icon}</Text>
              <View style={styles.forecastBody}>
                <Text style={[styles.forecastName, { color: accent }]}>
                  {f.property.name}{district ? `（${district}）` : ''}
                </Text>
                <Text style={[styles.forecastPop, { color: accent }]}>
                  未來 6 小時降雨機率 {f.maxPop6h}%
                </Text>
                {hint && <Text style={[styles.forecastHint, { color: accent }]}>{hint}</Text>}
              </View>
            </View>
          );
        })}
      </View>
    );
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#2E75B6" />
        <Text style={styles.loadingText}>載入中…</Text>
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
    >
      <View style={styles.sectionHeader}>
        <Ionicons name="stats-chart-outline" size={15} color="#888" />
        <Text style={styles.sectionHeaderText}>財產風險狀態</Text>
      </View>
      {renderRisksSection()}

      <View style={styles.sectionHeader}>
        <Ionicons name="rainy-outline" size={15} color="#888" />
        <Text style={styles.sectionHeaderText}>財產所在地降雨預報</Text>
      </View>
      {renderForecastSection()}
    </ScrollView>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F0F4F8' },
  content: { padding: 16, gap: 12, paddingBottom: 32 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#F0F4F8', gap: 10 },
  loadingText: { fontSize: 14, color: '#aaa' },

  sectionHeader: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 6, paddingHorizontal: 4 },
  sectionHeaderText: { fontSize: 12, color: '#888', fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.5, flex: 1 },

  // 財產風險
  risksLoading: { flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: '#fff', borderRadius: 12, padding: 16 },
  risksLoadingText: { fontSize: 13, color: '#aaa' },
  risksGroup: { gap: 8 },
  allSafeWrap: { backgroundColor: '#E8F8EF', borderRadius: 12, padding: 14, gap: 6 },
  allSafeRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  allSafeText: { fontSize: 14, color: '#27AE60', fontWeight: '600' },
  lastAlertText: { fontSize: 12, color: '#888', paddingLeft: 23 },
  collapsedRow: { flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: '#F5FBF7', borderRadius: 10, padding: 12 },
  collapsedText: { fontSize: 13, color: '#27AE60' },

  riskCard: {
    backgroundColor: '#fff', borderRadius: 12, padding: 14,
    borderLeftWidth: 4,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.06, shadowRadius: 4, elevation: 2,
  },
  riskCardTop: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  riskPropName: { flex: 1, fontSize: 14, fontWeight: '600', color: '#1A1A2E' },
  riskBadge: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 8, paddingVertical: 3, borderRadius: 8 },
  riskPctText: { fontSize: 13, fontWeight: '700' },
  riskLevelText: { fontSize: 11, fontWeight: '600' },
  riskDivider: { height: 1, backgroundColor: '#F0F0F0', marginVertical: 10 },
  riskRainfallText: { fontSize: 13, color: '#555', marginBottom: 6 },
  riskAdviceRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 6 },
  riskAdviceText: { fontSize: 12, color: '#888', flex: 1, lineHeight: 17 },

  // 降雨預報
  forecastGroup: { gap: 8 },
  forecastIntro: { fontSize: 12, color: '#888', paddingHorizontal: 4, marginBottom: 2 },
  forecastCard: {
    borderRadius: 12, padding: 14, flexDirection: 'row', alignItems: 'center', gap: 12,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.06, shadowRadius: 4, elevation: 2,
  },
  forecastIcon: { fontSize: 30 },
  forecastBody: { flex: 1, gap: 3 },
  forecastName: { fontSize: 13, fontWeight: '600' },
  forecastPop: { fontSize: 16, fontWeight: '700' },
  forecastHint: { fontSize: 12, fontWeight: '500', marginTop: 1 },
  forecastNoData: { fontSize: 13, color: '#aaa', textAlign: 'center', flex: 1 },
});
