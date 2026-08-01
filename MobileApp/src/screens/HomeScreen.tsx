import { useState, useCallback, useMemo } from 'react';
import {
  View, Text, StyleSheet,
  ActivityIndicator, ScrollView, RefreshControl,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import Svg, { Circle, Ellipse, Path, Line, G } from 'react-native-svg';
import { apiFetch } from '../lib/api';

// ─── Types ────────────────────────────────────────────────────────────────────

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

// ─── State config ─────────────────────────────────────────────────────────────

type DollState = 'sunny' | 'cloudy' | 'level2' | 'level1';

// 測試用：改成 'sunny' | 'cloudy' | 'level2' | 'level1' 強制顯示特定狀態
const DEBUG_STATE: DollState | null = null;

// 測試用：設定假財產，讓二級/一級的行動建議列表可以顯示
const DEBUG_FAKE_ALERTS: { name: string; type: string; riskLevel: 'warning' | 'critical' }[] | null = null;

const STATE_BG: Record<DollState, string> = {
  sunny:  '#dcefff',
  cloudy: '#eef1f5',
  level2: '#fff4d6',
  level1: '#ffe4e4',
};

const STATE_TEXT: Record<DollState, string> = {
  sunny:  '#2c6cb0',
  cloudy: '#5a6b78',
  level2: '#a6791a',
  level1: '#b52d2d',
};

const STATE_LABEL: Record<DollState, string> = {
  sunny:  '大晴天',
  cloudy: '多雲',
  level2: '二級預警',
  level1: '一級警戒',
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function buildRisk(property: Property, thr: any): PropertyRisk {
  const empty: PropertyRisk = {
    property, riskPct: 0, riskLevel: 'safe',
    topScale: null, topMm: null, topThreshold: null, hasData: false,
  };
  if (!thr || thr.error) return empty;

  const cr       = thr.current_rainfall as { '1h': number; '3h': number; '6h': number } | undefined;
  const t2       = thr.thresholds?.level2 as { '1h': number | null; '3h': number | null; '6h': number | null } | undefined;
  const apiLevel = thr.level as 'safe' | 'level2' | 'level1' | undefined;

  const candidates: { scale: string; mm: number; threshold: number; pct: number }[] = [];
  if (cr?.['1h'] != null && t2?.['1h']) candidates.push({ scale: '1H', mm: cr['1h'], threshold: t2['1h']!, pct: cr['1h'] / t2['1h']! * 100 });
  if (cr?.['3h'] != null && t2?.['3h']) candidates.push({ scale: '3H', mm: cr['3h'], threshold: t2['3h']!, pct: cr['3h'] / t2['3h']! * 100 });
  if (cr?.['6h'] != null && t2?.['6h']) candidates.push({ scale: '6H', mm: cr['6h'], threshold: t2['6h']!, pct: cr['6h'] / t2['6h']! * 100 });

  if (candidates.length === 0) {
    if (apiLevel === 'level1') return { ...empty, property, riskLevel: 'critical', hasData: true };
    if (apiLevel === 'level2') return { ...empty, property, riskLevel: 'warning',  hasData: true };
    return empty;
  }

  const top = candidates.reduce((a, b) => a.pct > b.pct ? a : b);
  let riskLevel: PropertyRisk['riskLevel'];
  if      (apiLevel === 'level1') riskLevel = 'critical';
  else if (apiLevel === 'level2') riskLevel = 'warning';
  else riskLevel = top.pct >= 80 ? 'notice' : 'safe';

  return { property, riskPct: top.pct, riskLevel, topScale: top.scale, topMm: top.mm, topThreshold: top.threshold, hasData: true };
}

function getAdviceForLevel(riskLevel: PropertyRisk['riskLevel'], type: string): string {
  const key = riskLevel === 'critical' ? 'level1' : 'level2';
  const map: Record<string, Record<string, string>> = {
    level1: {
      house:     '緊急：一樓人員注意安全，切勿進入地下室',
      car:       '緊急：立即移車，遠離低窪停車區',
      warehouse: '緊急：關閉電源總開關，人員撤離',
      other:     '緊急：遠離淹水區域，注意人身安全',
    },
    level2: {
      house:     '貴重物品、家電移至高處，確認一樓門窗防水',
      car:       '盡快將車輛移往高處停放',
      warehouse: '墊高庫存，確認電源總開關位置',
      other:     '重要物品移至高處，密切關注水情',
    },
  };
  return map[key][type] ?? map[key].other;
}

function formatAlertDate(isoStr: string): string {
  const d = new Date(isoStr.endsWith('Z') || isoStr.includes('+') ? isoStr : isoStr + 'Z');
  return d.toLocaleDateString('zh-TW', { month: 'numeric', day: 'numeric' });
}

// ─── EmojiFace ────────────────────────────────────────────────────────────────
// viewBox 0 0 150 140   face: cx=68 cy=65 r=42

function EmojiFace({ state, size = 160 }: { state: DollState; size?: number }) {
  const FACE_FILL: Record<DollState, string> = {
    sunny:  '#ffd23f',
    cloudy: '#dde4ea',
    level2: '#f5c344',
    level1: '#e8797d',
  };
  const fc = FACE_FILL[state];
  const F  = '#5a5f6b';
  const cx = 68, cy = 65, r = 42;

  return (
    <Svg width={size} height={size * 140 / 150} viewBox="0 0 150 140">

      {/* ── Sun rays (sunny) ── */}
      {state === 'sunny' && [0, 45, 90, 135, 180, 225, 270, 315].map(deg => {
        const rad = deg * Math.PI / 180;
        return (
          <Line key={deg}
            x1={cx + 50 * Math.cos(rad)} y1={cy + 50 * Math.sin(rad)}
            x2={cx + 63 * Math.cos(rad)} y2={cy + 63 * Math.sin(rad)}
            stroke="#ffd23f" strokeWidth={4} strokeLinecap="round"
          />
        );
      })}

      {/* ── Rain drops below face ── */}
      {(state === 'level2' || state === 'level1') && (
        <G>
          <Line x1={40} y1={111} x2={38} y2={122} stroke="#7faabb" strokeWidth={2.5} strokeLinecap="round" />
          <Line x1={64} y1={111} x2={62} y2={122} stroke="#7faabb" strokeWidth={2.5} strokeLinecap="round" />
          <Line x1={88} y1={111} x2={86} y2={122} stroke="#7faabb" strokeWidth={2.5} strokeLinecap="round" />
          {state === 'level1' && (
            <G>
              <Line x1={30} y1={122} x2={28} y2={133} stroke="#7faabb" strokeWidth={2.5} strokeLinecap="round" />
              <Line x1={54} y1={122} x2={52} y2={133} stroke="#7faabb" strokeWidth={2.5} strokeLinecap="round" />
              <Line x1={78} y1={122} x2={76} y2={133} stroke="#7faabb" strokeWidth={2.5} strokeLinecap="round" />
              <Line x1={102} y1={122} x2={100} y2={133} stroke="#7faabb" strokeWidth={2.5} strokeLinecap="round" />
            </G>
          )}
        </G>
      )}

      {/* ── Face circle ── */}
      <Circle cx={cx} cy={cy} r={r} fill={fc} />

      {/* ── Eyebrows ── */}
      {state === 'level2' && (
        <G>
          {/* 憤怒眉: outer UP inner DOWN (furrowed/angry) */}
          <Path d="M 44 46 L 60 53" stroke={F} strokeWidth={3.5} strokeLinecap="round" />
          <Path d="M 76 53 L 92 46" stroke={F} strokeWidth={3.5} strokeLinecap="round" />
        </G>
      )}
      {state === 'level1' && (
        <G>
          {/* 更深憤怒眉: steeper + thicker */}
          <Path d="M 42 43 L 60 52" stroke="#7a1c1c" strokeWidth={4.5} strokeLinecap="round" />
          <Path d="M 76 52 L 94 43" stroke="#7a1c1c" strokeWidth={4.5} strokeLinecap="round" />
        </G>
      )}

      {/* ── Eyes ── */}
      {state === 'sunny' && (
        <G>
          {/* ^^ 彎彎笑眼 */}
          <Path d="M 46 62 Q 53 53 60 62" stroke={F} strokeWidth={3}   fill="none" strokeLinecap="round" />
          <Path d="M 76 62 Q 83 53 90 62" stroke={F} strokeWidth={3}   fill="none" strokeLinecap="round" />
          {/* 腮紅 */}
          <Ellipse cx={40} cy={72} rx={8} ry={4.5} fill="#F48FB1" opacity={0.55} />
          <Ellipse cx={96} cy={72} rx={8} ry={4.5} fill="#F48FB1" opacity={0.55} />
        </G>
      )}
      {state === 'cloudy' && (
        <G>
          <Circle cx={53} cy={64} r={5}   fill={F} />
          <Circle cx={83} cy={64} r={5}   fill={F} />
        </G>
      )}
      {state === 'level2' && (
        <G>
          <Ellipse cx={53} cy={64} rx={5.5} ry={4.5} fill={F} />
          <Ellipse cx={83} cy={64} rx={5.5} ry={4.5} fill={F} />
        </G>
      )}
      {state === 'level1' && (
        <G>
          <Circle cx={53} cy={64} r={8}   fill="white" />
          <Circle cx={83} cy={64} r={8}   fill="white" />
          <Circle cx={53} cy={64} r={4.5} fill={F} />
          <Circle cx={83} cy={64} r={4.5} fill={F} />
        </G>
      )}

      {/* ── Mouth ── */}
      {state === 'sunny'  && <Path d="M 46 79 Q 68 97 90 79" stroke={F} strokeWidth={3}   fill="none" strokeLinecap="round" />}
      {state === 'cloudy' && <Path d="M 50 79 Q 68 89 86 79" stroke={F} strokeWidth={2.5} fill="none" strokeLinecap="round" />}
      {state === 'level2' && <Path d="M 53 81 Q 61 76 68 81 Q 75 86 83 81" stroke={F} strokeWidth={2.5} fill="none" strokeLinecap="round" />}
      {state === 'level1' && <Ellipse cx={68} cy={83} rx={10} ry={9} fill="#7a1c1c" />}

      {/* ── Cloud on top of face (cloudy) — drawn last so it's above face ── */}
      {state === 'cloudy' && (
        <Path
          d="M 82 48 Q 80 43 84 40 Q 86 33 93 34 Q 95 28 101 28 Q 108 28 110 33 Q 115 30 119 36 Q 123 40 120 46 Q 119 48 115 48 Z"
          fill="#ffffff"
          stroke="#c8d0d8"
          strokeWidth={1}
        />
      )}

    </Svg>
  );
}

// ─── HomeScreen ───────────────────────────────────────────────────────────────

export default function HomeScreen() {
  const [alerts, setAlerts]               = useState<Alert[]>([]);
  const [propertyRisks, setPropertyRisks] = useState<PropertyRisk[]>([]);
  const [forecastList, setForecastList]   = useState<PropertyForecast[]>([]);
  const [loading, setLoading]             = useState(true);
  const [risksLoading, setRisksLoading]   = useState(true);
  const [forecastLoading, setForecastLoading] = useState(true);
  const [refreshing, setRefreshing]       = useState(false);

  const fetchPropertyRisks = async (properties: Property[]): Promise<PropertyRisk[]> => {
    const results = await Promise.all(
      properties.map(async (p) => {
        try {
          const res = await apiFetch(`/api/threshold?lat=${p.latitude}&lng=${p.longitude}`);
          if (!res.ok) return buildRisk(p, null);
          return buildRisk(p, await res.json());
        } catch {
          return buildRisk(p, null);
        }
      })
    );
    return results.sort((a, b) => b.riskPct - a.riskPct);
  };

  const fetchForecasts = async (properties: Property[]): Promise<void> => {
    const results = await Promise.all(
      properties.map(async (p) => {
        try {
          const resp = await apiFetch(`/api/forecast?lat=${p.latitude}&lng=${p.longitude}`);
          if (!resp.ok) return null;
          const data = await resp.json();
          if (data.max_pop_6h === null) return null;
          return { property: p, districtName: data.district_name as string | null, maxPop6h: data.max_pop_6h as number };
        } catch {
          return null;
        }
      })
    );
    setForecastList(
      results
        .filter((r): r is PropertyForecast => r !== null && r.maxPop6h >= 30)
        .sort((a, b) => b.maxPop6h - a.maxPop6h)
    );
    setForecastLoading(false);
  };

  const fetchData = async () => {
    const [alertResult, propertiesResult] = await Promise.allSettled([
      apiFetch('/api/alerts'),
      apiFetch('/api/properties'),
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

  // ── State derivation ─────────────────────────────────────────────────────────

  const dollState = useMemo((): DollState => {
    if (DEBUG_STATE) return DEBUG_STATE;
    if (propertyRisks.some(r => r.riskLevel === 'critical')) return 'level1';
    if (propertyRisks.some(r => r.riskLevel === 'warning'))  return 'level2';
    if (propertyRisks.some(r => r.topMm != null && r.topMm > 0)) return 'cloudy';
    return 'sunny';
  }, [propertyRisks]);

  const stateText    = STATE_TEXT[dollState];
  const stateBg      = STATE_BG[dollState];
  const isSafe       = dollState === 'sunny' || dollState === 'cloudy';
  const alertedRisks: PropertyRisk[] = DEBUG_FAKE_ALERTS
    ? DEBUG_FAKE_ALERTS.map(d => ({
        property: { id: d.name, name: d.name, type: d.type, latitude: 0, longitude: 0, district_name: null },
        riskPct: 100, riskLevel: d.riskLevel, topScale: null, topMm: null, topThreshold: null, hasData: false,
      }))
    : propertyRisks.filter(r => r.riskLevel === 'critical' || r.riskLevel === 'warning');

  // ── Render ───────────────────────────────────────────────────────────────────

  const renderForecast = () => {
    if (forecastLoading) {
      return (
        <View style={[styles.forecastCard, { backgroundColor: 'rgba(255,255,255,0.45)' }]}>
          <ActivityIndicator size="small" color={stateText} />
          <Text style={[styles.forecastLoadText, { color: stateText }]}>查詢降雨預報中…</Text>
        </View>
      );
    }
    if (forecastList.length === 0) {
      return (
        <Text style={[styles.forecastEmpty, { color: stateText }]}>暫無預報資料</Text>
      );
    }
    const ICON = ['☀️', '🌦️', '🌧️', '⛈️'];
    const getIcon = (pop: number) => pop < 20 ? ICON[0] : pop < 50 ? ICON[1] : pop < 70 ? ICON[2] : ICON[3];

    return (
      <View style={styles.forecastGroup}>
        {forecastList.map(f => {
          const district = f.districtName ?? f.property.district_name ?? '';
          return (
            <View key={f.property.id} style={[styles.forecastCard, { backgroundColor: 'rgba(255,255,255,0.50)' }]}>
              <Text style={styles.forecastIcon}>{getIcon(f.maxPop6h)}</Text>
              <View style={styles.forecastBody}>
                <Text style={[styles.forecastName, { color: stateText }]} numberOfLines={1}>
                  {f.property.name}{district ? `（${district}）` : ''}
                </Text>
                <Text style={[styles.forecastPop, { color: stateText }]}>
                  未來 6 小時降雨機率 {f.maxPop6h}%
                </Text>
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
        <Text style={styles.centerText}>載入中…</Text>
      </View>
    );
  }

  return (
    <ScrollView
      style={[styles.scroll, { backgroundColor: stateBg }]}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={stateText} />
      }
    >
      {/* ── Hero ── */}
      <View style={styles.hero}>
        {risksLoading ? (
          <ActivityIndicator size="large" color={stateText} style={{ marginVertical: 70 }} />
        ) : (
          <>
            <EmojiFace state={dollState} size={160} />

            <Text style={[styles.stateLabel, { color: stateText }]}>
              {STATE_LABEL[dollState]}
            </Text>

            {isSafe ? (
              <View style={styles.safeInfo}>
                <Text style={[styles.safeText, { color: stateText }]}>
                  你的財產都在安全範圍
                </Text>
                <Text style={[styles.lastAlertText, { color: stateText }]}>
                  {alerts.length > 0
                    ? `最近一次警報：${formatAlertDate(alerts[0].created_at)}`
                    : '尚無警報記錄'}
                </Text>
              </View>
            ) : (
              <View style={styles.adviceList}>
                {alertedRisks.slice(0, 4).map(r => (
                  <View key={r.property.id} style={[styles.adviceRow, { borderLeftColor: stateText + 'aa' }]}>
                    <Text style={[styles.advicePropName, { color: stateText }]}>
                      {r.property.name}
                    </Text>
                    <Text style={[styles.adviceText, { color: stateText }]}>
                      {getAdviceForLevel(r.riskLevel, r.property.type)}
                    </Text>
                  </View>
                ))}
              </View>
            )}
          </>
        )}
      </View>

      {/* ── Forecast ── */}
      <View style={styles.forecastSection}>
        <View style={styles.sectionHeader}>
          <Ionicons name="rainy-outline" size={14} color={stateText} opacity={0.7} />
          <Text style={[styles.sectionHeaderText, { color: stateText }]}>
            財產所在地降雨預報
          </Text>
        </View>
        {renderForecast()}
      </View>
    </ScrollView>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  scroll:   { flex: 1 },
  content:  { paddingBottom: 48 },
  center:   { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#F0F4F8', gap: 10 },
  centerText: { fontSize: 14, color: '#aaa' },

  // ── Hero ──
  hero: {
    paddingTop: 28,
    paddingBottom: 36,
    paddingHorizontal: 28,
    alignItems: 'center',
  },
  stateLabel: {
    fontSize: 28,
    fontWeight: '800',
    marginTop: 10,
    letterSpacing: 0.5,
  },
  safeInfo: {
    alignItems: 'center',
    marginTop: 10,
    gap: 5,
  },
  safeText: {
    fontSize: 15,
    fontWeight: '500',
    opacity: 0.88,
  },
  lastAlertText: {
    fontSize: 12,
    opacity: 0.5,
  },
  adviceList: {
    width: '100%',
    marginTop: 18,
    gap: 14,
  },
  adviceRow: {
    borderLeftWidth: 3,
    paddingLeft: 12,
    gap: 3,
  },
  advicePropName: {
    fontSize: 14,
    fontWeight: '700',
  },
  adviceText: {
    fontSize: 13,
    lineHeight: 19,
    opacity: 0.82,
  },

  // ── Forecast ──
  forecastSection: {
    paddingHorizontal: 16,
    paddingBottom: 8,
    gap: 10,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 2,
    marginBottom: 2,
  },
  sectionHeaderText: {
    fontSize: 12,
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    opacity: 0.7,
  },
  forecastGroup: { gap: 8 },
  forecastCard: {
    borderRadius: 14,
    padding: 14,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  forecastIcon:     { fontSize: 28 },
  forecastBody:     { flex: 1, gap: 3 },
  forecastName:     { fontSize: 13, fontWeight: '600' },
  forecastPop:      { fontSize: 16, fontWeight: '700' },
  forecastLoadText: { fontSize: 13, opacity: 0.7 },
  forecastEmpty:    { fontSize: 13, textAlign: 'center', paddingVertical: 16, opacity: 0.5 },
});
