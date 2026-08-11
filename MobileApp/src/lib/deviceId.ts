import AsyncStorage from '@react-native-async-storage/async-storage';

const STORAGE_KEY = 'app_device_id';

let _cached: string | null = null;

export async function getDeviceId(): Promise<string> {
  if (_cached) return _cached;

  const stored = await AsyncStorage.getItem(STORAGE_KEY);
  if (stored) {
    _cached = stored;
    return stored;
  }

  const newId = (typeof crypto !== 'undefined' && crypto.randomUUID)
    ? crypto.randomUUID()
    : 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
        const r = (Math.random() * 16) | 0;
        return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
      });
  await AsyncStorage.setItem(STORAGE_KEY, newId);
  _cached = newId;
  return newId;
}
