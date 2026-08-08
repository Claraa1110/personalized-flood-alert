import { StatusBar } from 'expo-status-bar';
import AppNavigator from './src/navigation/AppNavigator';
import ErrorBoundary, { reportGlobalError } from './src/components/ErrorBoundary';

// ── 全域 JS 錯誤捕捉（在 React 渲染之前設定，模組載入錯誤也能捕捉到）──
const _origHandler =
  (global as any).ErrorUtils?.getGlobalHandler?.() ?? (() => {});

(global as any).ErrorUtils?.setGlobalHandler?.((error: Error, isFatal: boolean) => {
  const label = isFatal ? 'FATAL' : 'non-fatal';
  const msg = `[${label}] ${error?.message ?? String(error)}\n${error?.stack ?? '(no stack)'}`;
  console.error('[GlobalHandler]', msg);
  reportGlobalError(msg);
  _origHandler(error, isFatal);
});

export default function App() {
  return (
    <ErrorBoundary>
      <AppNavigator />
      <StatusBar style="auto" />
    </ErrorBoundary>
  );
}
