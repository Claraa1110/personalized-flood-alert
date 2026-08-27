import AsyncStorage from '@react-native-async-storage/async-storage';
import { apiFetch } from './api';
import { PropertyType } from './advice';

export interface PropertyWithRisk {
  id: string;
  name: string;
  type: PropertyType | null;
  custom_type_name?: string | null;
  address: string | null;
  district_name: string | null;
  latitude: number;
  longitude: number;
  rainfall: { '1h': number; '3h': number; '6h': number };
  level: 'safe' | 'level2' | 'level1';
  risk_action: string | null;
  risk_pct: number;
  priority_stars: number;
}

export const PROPERTY_TTL = 5 * 60 * 1000;   // 5 分鐘
export const FORECAST_TTL = 30 * 60 * 1000;  // 30 分鐘

const STORAGE_KEY = 'cached_properties';

// ── Module-level singleton：HomeScreen / PropertyListScreen 共用 ──────────────

let _cache: PropertyWithRisk[] = [];
let _fetchedAt = 0;
let _forecastCachedAt = 0;
let _inflight: Promise<PropertyWithRisk[]> | null = null;

export function getCachedProperties(): PropertyWithRisk[] {
  return _cache;
}

export function isPropertyCacheFresh(): boolean {
  return _cache.length > 0 && Date.now() - _fetchedAt < PROPERTY_TTL;
}

export function getForecastCachedAt(): number { return _forecastCachedAt; }
export function setForecastCachedAt(t: number): void { _forecastCachedAt = t; }

export function invalidatePropertyCache(): void {
  _fetchedAt = 0;
  _forecastCachedAt = 0;  // 同時讓預報快取失效，新增財產後首頁預報也會重抓
}

/**
 * App 啟動時呼叫一次：從 AsyncStorage 讀取上次的財產快取，
 * 直接填入 _cache 供各頁面立即顯示，但不標為 fresh（會由 useFocusEffect 觸發後端校正）
 */
export async function loadPersistedProperties(): Promise<void> {
  try {
    const json = await AsyncStorage.getItem(STORAGE_KEY);
    if (json) {
      const data: PropertyWithRisk[] = JSON.parse(json);
      if (Array.isArray(data) && data.length > 0) {
        _cache = data;
        // _fetchedAt 維持 0，確保下次 fetchPropertiesWithRisk 一定會打後端校正
      }
    }
  } catch {
    // 讀取失敗就當作沒有快取，不影響正常流程
  }
}

/** 共用的抓取函式：相同 inflight 不會重複打 API；成功後同步寫入 AsyncStorage */
export async function fetchPropertiesWithRisk(force = false): Promise<PropertyWithRisk[]> {
  if (!force && isPropertyCacheFresh()) return _cache;
  if (_inflight) return _inflight;

  _inflight = (async () => {
    const resp = await apiFetch('/api/properties-with-risk');
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data: PropertyWithRisk[] = await resp.json();
    _cache = data;
    _fetchedAt = Date.now();
    // 後端成功後寫入本地（fire-and-forget，不阻塞 UI）
    AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(data)).catch(() => {});
    return data;
  })().finally(() => { _inflight = null; });

  return _inflight;
}
