import { Platform } from 'react-native';
import { changeIcon } from 'react-native-change-icon';

export async function syncAppIcon(hasAlert: boolean): Promise<void> {
  if (Platform.OS !== 'android') return;

  const targetIcon = hasAlert ? 'Alert' : 'Default';
  try {
    await changeIcon(targetIcon);
  } catch (e: any) {
    // ICON_ALREADY_USED is expected when the correct icon is already active; ignore it.
    // Any other error is silently swallowed to avoid crashing the app.
  }
}
