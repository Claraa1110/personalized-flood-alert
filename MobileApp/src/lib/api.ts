import { getDeviceId } from './deviceId';

const CLOUD_URL = 'https://ff-weathered-paper-9628.fly.dev';
const BASE = process.env.EXPO_PUBLIC_API_URL
  ?? (__DEV__ ? 'http://localhost:8001' : CLOUD_URL);

const TIMEOUT_MS = 15_000;

export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const deviceId = await getDeviceId();
  const headers = new Headers(init.headers);
  headers.set('X-Device-Id', deviceId);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    return await fetch(`${BASE}${path}`, { ...init, headers, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

/**
 * 從後端錯誤回應中取出可顯示的文字。
 * 自訂的 HTTPException 的 detail 是字串；FastAPI 自動驗證錯誤（422）的
 * detail 則是 Pydantic 錯誤物件陣列，需另外取出 msg 欄位組成字串。
 */
export function extractErrorMessage(body: any, fallback: string): string {
  const detail = body?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    const msgs = detail.map((d) => d?.msg).filter(Boolean);
    if (msgs.length > 0) return msgs.join('；');
  }
  return fallback;
}
