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
