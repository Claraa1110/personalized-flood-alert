import React, { Component, ErrorInfo } from 'react';
import { View, Text, ScrollView, StyleSheet, TouchableOpacity } from 'react-native';

// Module-level store so the global handler (set before React renders) can feed errors in
const _pendingGlobalErrors: string[] = [];
const _stateUpdaters: Array<(msgs: string[]) => void> = [];

export function reportGlobalError(message: string) {
  _pendingGlobalErrors.push(message);
  _stateUpdaters.forEach(fn => fn([..._pendingGlobalErrors]));
}

interface State {
  reactError: string | null;
  globalErrors: string[];
}

export default class ErrorBoundary extends Component<{ children: React.ReactNode }, State> {
  state: State = { reactError: null, globalErrors: [] };

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { reactError: `${error.toString()}\n\n${error.stack ?? ''}` };
  }

  componentDidCatch(_error: Error, info: ErrorInfo) {
    this.setState(prev => ({
      reactError: (prev.reactError ?? '') + '\n\n[componentStack]\n' + (info.componentStack ?? ''),
    }));
  }

  componentDidMount() {
    _stateUpdaters.push(msgs => this.setState({ globalErrors: msgs }));
    // Drain any errors that arrived before mount
    if (_pendingGlobalErrors.length > 0) {
      this.setState({ globalErrors: [..._pendingGlobalErrors] });
    }
  }

  componentWillUnmount() {
    const idx = _stateUpdaters.findIndex(fn => fn.toString().includes('globalErrors'));
    if (idx >= 0) _stateUpdaters.splice(idx, 1);
  }

  render() {
    const { reactError, globalErrors } = this.state;
    const hasError = reactError || globalErrors.length > 0;

    if (!hasError) return this.props.children;

    const fullLog = [
      reactError ? `[React Render Error]\n${reactError}` : null,
      ...globalErrors.map((e, i) => `[Global Error ${i + 1}]\n${e}`),
    ]
      .filter(Boolean)
      .join('\n\n─────────────────────\n\n');

    return (
      <View style={s.root}>
        <Text style={s.title}>💥 App Crash Log</Text>
        <Text style={s.sub}>截圖這個畫面，或長按文字選取複製後回報</Text>
        <ScrollView style={s.scroll} contentContainerStyle={{ padding: 12 }}>
          <Text style={s.log} selectable>{fullLog}</Text>
        </ScrollView>
        <TouchableOpacity
          style={s.retryBtn}
          onPress={() => this.setState({ reactError: null, globalErrors: [] })}
        >
          <Text style={s.retryText}>重試</Text>
        </TouchableOpacity>
      </View>
    );
  }
}

const s = StyleSheet.create({
  root:      { flex: 1, backgroundColor: '#111', paddingTop: 60, paddingHorizontal: 16 },
  title:     { color: '#ff5555', fontSize: 22, fontWeight: '800', marginBottom: 4 },
  sub:       { color: '#888', fontSize: 13, marginBottom: 12 },
  scroll:    { flex: 1, backgroundColor: '#1a1a1a', borderRadius: 8 },
  log:       { color: '#e0e0e0', fontSize: 11, lineHeight: 17, fontFamily: 'monospace' },
  copyBtn:   { backgroundColor: '#2e75b6', padding: 14, borderRadius: 10, marginTop: 10, alignItems: 'center' },
  copyText:  { color: '#fff', fontWeight: '700', fontSize: 15 },
  retryBtn:  { backgroundColor: '#333', padding: 12, borderRadius: 10, marginTop: 8, alignItems: 'center' },
  retryText: { color: '#ccc', fontSize: 14 },
});
