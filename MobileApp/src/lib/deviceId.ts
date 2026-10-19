import * as SecureStore from 'expo-secure-store';
import AsyncStorage from '@react-native-async-storage/async-storage';

const SECURE_KEY = 'app_device_id';
const LEGACY_KEY = 'app_device_id'; // AsyncStorage 舊 key（同名）

let _cached: string | null = null;

function generateUUID(): string {
  return (typeof crypto !== 'undefined' && crypto.randomUUID)
    ? crypto.randomUUID()
    : 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
        const r = (Math.random() * 16) | 0;
        return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
      });
}

export async function getDeviceId(): Promise<string> {
  if (_cached) return _cached;

  try {
    // 1. 優先從 SecureStore 讀取（已遷移的使用者 / 新使用者）
    const stored = await SecureStore.getItemAsync(SECURE_KEY);
    if (stored) {
      _cached = stored;
      return stored;
    }

    // 2. 遷移：讀舊的 AsyncStorage
    const legacy = await AsyncStorage.getItem(LEGACY_KEY);
    if (legacy) {
      await SecureStore.setItemAsync(SECURE_KEY, legacy);
      AsyncStorage.removeItem(LEGACY_KEY).catch(() => {}); // fire-and-forget
      _cached = legacy;
      return legacy;
    }

    // 3. 首次安裝：產生新 UUID 存入 SecureStore
    const newId = generateUUID();
    await SecureStore.setItemAsync(SECURE_KEY, newId);
    _cached = newId;
    return newId;
  } catch {
    // SecureStore 異常時，回退到 session-only UUID，避免 App crash
    if (!_cached) _cached = generateUUID();
    return _cached;
  }
}
