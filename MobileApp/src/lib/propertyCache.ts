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
}

export const PROPERTY_TTL = 5 * 60 * 1000;   // 5 分鐘
export const FORECAST_TTL = 30 * 60 * 1000;  // 30 分鐘

// ── Module-level singleton：HomeScreen / PropertyListScreen 共用 ──────────────

let _cache: PropertyWithRisk[] = [];
let _fetchedAt = 0;
let _inflight: Promise<PropertyWithRisk[]> | null = null;

export function getCachedProperties(): PropertyWithRisk[] {
  return _cache;
}

export function isPropertyCacheFresh(): boolean {
  return _cache.length > 0 && Date.now() - _fetchedAt < PROPERTY_TTL;
}

export function invalidatePropertyCache(): void {
  _fetchedAt = 0;
}

/** 共用的抓取函式：相同 inflight 不會重複打 API */
export async function fetchPropertiesWithRisk(force = false): Promise<PropertyWithRisk[]> {
  if (!force && isPropertyCacheFresh()) return _cache;
  if (_inflight) return _inflight;

  _inflight = (async () => {
    const resp = await apiFetch('/api/properties-with-risk');
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data: PropertyWithRisk[] = await resp.json();
    _cache = data;
    _fetchedAt = Date.now();
    return data;
  })().finally(() => { _inflight = null; });

  return _inflight;
}
