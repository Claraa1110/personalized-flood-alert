import { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  ActivityIndicator, KeyboardAvoidingView, Platform, ScrollView,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { supabase } from '../lib/supabase';

interface Props {
  onGoRegister: () => void;
}

export default function LoginScreen({ onGoRegister }: Props) {
  const [email, setEmail]       = useState('');
  const [password, setPassword] = useState('');
  const [showPw, setShowPw]     = useState(false);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState<string | null>(null);

  const handleLogin = async () => {
    if (!email.trim() || !password) { setError('請輸入 Email 和密碼'); return; }
    setLoading(true);
    setError(null);
    const { error: e } = await supabase.auth.signInWithPassword({
      email: email.trim(),
      password,
    });
    if (e) setError(e.message);
    setLoading(false);
  };

  return (
    <KeyboardAvoidingView
      style={styles.root}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
        {/* Logo area */}
        <View style={styles.logoArea}>
          <View style={styles.logoCircle}>
            <Ionicons name="shield-checkmark" size={40} color="#fff" />
          </View>
          <Text style={styles.appName}>淹水預警</Text>
          <Text style={styles.tagline}>守護你的財產安全</Text>
        </View>

        {/* Form */}
        <View style={styles.card}>
          <Text style={styles.title}>登入</Text>

          <Text style={styles.label}>電子郵件</Text>
          <TextInput
            style={styles.input}
            value={email}
            onChangeText={setEmail}
            placeholder="your@email.com"
            placeholderTextColor="#bbb"
            keyboardType="email-address"
            autoCapitalize="none"
            autoCorrect={false}
          />

          <Text style={styles.label}>密碼</Text>
          <View style={styles.pwWrap}>
            <TextInput
              style={styles.pwInput}
              value={password}
              onChangeText={setPassword}
              placeholder="請輸入密碼"
              placeholderTextColor="#bbb"
              secureTextEntry={!showPw}
              autoCapitalize="none"
            />
            <TouchableOpacity onPress={() => setShowPw(v => !v)} style={styles.eyeBtn}>
              <Ionicons name={showPw ? 'eye-off-outline' : 'eye-outline'} size={20} color="#aaa" />
            </TouchableOpacity>
          </View>

          {error ? (
            <View style={styles.errorBox}>
              <Ionicons name="alert-circle-outline" size={14} color="#C00000" />
              <Text style={styles.errorText}>{error}</Text>
            </View>
          ) : null}

          <TouchableOpacity style={styles.btn} onPress={handleLogin} disabled={loading}>
            {loading
              ? <ActivityIndicator color="#fff" />
              : <Text style={styles.btnText}>登入</Text>}
          </TouchableOpacity>
        </View>

        <TouchableOpacity style={styles.switchRow} onPress={onGoRegister}>
          <Text style={styles.switchText}>還沒有帳號？</Text>
          <Text style={styles.switchLink}>立即註冊</Text>
        </TouchableOpacity>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  root:   { flex: 1, backgroundColor: '#F0F4F8' },
  scroll: { flexGrow: 1, justifyContent: 'center', padding: 24 },

  logoArea: { alignItems: 'center', marginBottom: 32 },
  logoCircle: {
    width: 80, height: 80, borderRadius: 40,
    backgroundColor: '#2E75B6', alignItems: 'center', justifyContent: 'center',
    shadowColor: '#2E75B6', shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.35, shadowRadius: 12, elevation: 8, marginBottom: 14,
  },
  appName:  { fontSize: 26, fontWeight: '800', color: '#1A1A2E' },
  tagline:  { fontSize: 14, color: '#888', marginTop: 4 },

  card: {
    backgroundColor: '#fff', borderRadius: 20, padding: 24,
    shadowColor: '#000', shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.08, shadowRadius: 12, elevation: 6,
  },
  title: { fontSize: 22, fontWeight: '700', color: '#1A1A2E', marginBottom: 20, textAlign: 'center' },

  label: { fontSize: 13, fontWeight: '600', color: '#555', marginBottom: 6, marginTop: 12 },
  input: {
    borderWidth: 1.5, borderColor: '#E0E0E0', borderRadius: 12,
    paddingHorizontal: 14, paddingVertical: 12, fontSize: 15,
    color: '#222', backgroundColor: '#FAFAFA',
  },
  pwWrap: {
    flexDirection: 'row', alignItems: 'center',
    borderWidth: 1.5, borderColor: '#E0E0E0', borderRadius: 12,
    backgroundColor: '#FAFAFA',
  },
  pwInput: { flex: 1, paddingHorizontal: 14, paddingVertical: 12, fontSize: 15, color: '#222' },
  eyeBtn:  { paddingHorizontal: 14 },

  errorBox: {
    flexDirection: 'row', alignItems: 'center', gap: 6,
    backgroundColor: '#FFF0F0', borderRadius: 10, padding: 10, marginTop: 12,
  },
  errorText: { color: '#C00000', fontSize: 13, flex: 1 },

  btn: {
    backgroundColor: '#2E75B6', borderRadius: 14, paddingVertical: 14,
    alignItems: 'center', marginTop: 20,
    shadowColor: '#2E75B6', shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3, shadowRadius: 8, elevation: 5,
  },
  btnText: { color: '#fff', fontSize: 16, fontWeight: '700' },

  switchRow: { flexDirection: 'row', justifyContent: 'center', marginTop: 24, gap: 4 },
  switchText: { fontSize: 14, color: '#888' },
  switchLink: { fontSize: 14, color: '#2E75B6', fontWeight: '700' },
});
