import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';
import Constants from 'expo-constants';
import { Platform } from 'react-native';
import { apiFetch } from './api';

// 前景收到通知時也顯示 banner + 音效
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
    shouldShowBanner: true,
    shouldShowList: true,
  }),
});

export async function registerForPushNotifications(): Promise<void> {
  // 只在實體裝置執行
  if (!Device.isDevice) {
    console.log('[Push] 模擬器略過推播 token 註冊');
    return;
  }

  // Android 需要先建 notification channel
  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('default', {
      name: '淹水預警',
      importance: Notifications.AndroidImportance.MAX,
      vibrationPattern: [0, 250, 250, 250],
      lightColor: '#2E75B6',
    });
  }

  // 取得/請求權限
  const { status: existingStatus } = await Notifications.getPermissionsAsync();
  let finalStatus = existingStatus;
  if (existingStatus !== 'granted') {
    const { status } = await Notifications.requestPermissionsAsync();
    finalStatus = status;
  }
  if (finalStatus !== 'granted') {
    console.log('[Push] 使用者未授予推播權限，跳過');
    return;
  }

  // 取得 Expo Push Token
  const projectId =
    Constants.expoConfig?.extra?.eas?.projectId ||
    Constants.easConfig?.projectId;

  let tokenData: Notifications.ExpoPushToken;
  try {
    tokenData = await Notifications.getExpoPushTokenAsync(
      projectId ? { projectId } : undefined
    );
  } catch (e) {
    console.warn('[Push] 取得 token 失敗:', e);
    return;
  }

  const pushToken = tokenData.data;
  console.log('[Push] Expo Push Token:', pushToken);

  // 送到後端
  try {
    const resp = await apiFetch('/api/register-push-token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ push_token: pushToken }),
    });
    if (resp.ok) {
      console.log('[Push] Token 已成功註冊到後端');
    } else {
      console.warn('[Push] 後端回傳錯誤:', resp.status);
    }
  } catch (e) {
    console.warn('[Push] 送出 token 失敗:', e);
  }
}
