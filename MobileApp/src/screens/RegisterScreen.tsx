import { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  ActivityIndicator, KeyboardAvoidingView, Platform, ScrollView, Image,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { supabase } from '../lib/supabase';

interface Props {
  onGoLogin: () => void;
}

export default function RegisterScreen({ onGoLogin }: Props) {
  const [email, setEmail]       = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm]   = useState('');
  const [showPw, setShowPw]     = useState(false);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState<string | null>(null);
  const [success, setSuccess]   = useState(false);

  const handleRegister = async () => {
    if (!email.trim() || !password) { setError('請填寫所有欄位'); return; }
    if (password !== confirm) { setError('密碼與確認密碼不符'); return; }
    if (password.length < 6) { setError('密碼至少需要 6 個字元'); return; }

    setLoading(true);
    setError(null);
    const { error: e } = await supabase.auth.signUp({
      email: email.trim(),
      password,
      options: { emailRedirectTo: undefined },
    });
    if (e) {
      setError(e.message);
      setLoading(false);
      return;
    }
    // 嘗試直接登入（跳過 email 確認）
    const { error: loginErr } = await supabase.auth.signInWithPassword({
      email: email.trim(),
      password,
    });
    if (loginErr) {
      // 若需要 email 確認才能登入，顯示提示並跳回登入頁
      setSuccess(true);
    }
    setLoading(false);
  };

  if (success) {
    return (
      <View style={styles.root}>
        <View style={styles.successWrap}>
          <Ionicons name="checkmark-circle" size={64} color="#27AE60" />
          <Text style={styles.successTitle}>註冊成功！</Text>
          <Text style={styles.successSub}>請查收驗證信後登入</Text>
          <TouchableOpacity style={styles.btn} onPress={onGoLogin}>
            <Text style={styles.btnText}>前往登入</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      style={styles.root}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
        <View style={styles.logoArea}>
          <Image
            source={require('../../assets/icon.png')}
            style={styles.logoIcon}
          />
          <Text style={styles.appName}>水先知</Text>
          <Text style={styles.tagline}>建立你的帳號</Text>
        </View>

        <View style={styles.card}>
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
              placeholder="至少 6 個字元"
              placeholderTextColor="#bbb"
              secureTextEntry={!showPw}
              autoCapitalize="none"
            />
            <TouchableOpacity onPress={() => setShowPw(v => !v)} style={styles.eyeBtn}>
              <Ionicons name={showPw ? 'eye-off-outline' : 'eye-outline'} size={20} color="#aaa" />
            </TouchableOpacity>
          </View>

          <Text style={styles.label}>確認密碼</Text>
          <TextInput
            style={styles.input}
            value={confirm}
            onChangeText={setConfirm}
            placeholder="再次輸入密碼"
            placeholderTextColor="#bbb"
            secureTextEntry={!showPw}
            autoCapitalize="none"
          />

          {error ? (
            <View style={styles.errorBox}>
              <Ionicons name="alert-circle-outline" size={14} color="#C00000" />
              <Text style={styles.errorText}>{error}</Text>
            </View>
          ) : null}

          <TouchableOpacity style={styles.btn} onPress={handleRegister} disabled={loading}>
            {loading
              ? <ActivityIndicator color="#fff" />
              : <Text style={styles.btnText}>註冊</Text>}
          </TouchableOpacity>
        </View>

        <TouchableOpacity style={styles.switchRow} onPress={onGoLogin}>
          <Text style={styles.switchText}>已有帳號？</Text>
          <Text style={styles.switchLink}>前往登入</Text>
        </TouchableOpacity>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  root:   { flex: 1, backgroundColor: '#F0F4F8' },
  scroll: { flexGrow: 1, justifyContent: 'center', padding: 24 },

  logoArea: { alignItems: 'center', marginBottom: 28 },
  logoIcon: {
    width: 88, height: 88, borderRadius: 20,
    marginBottom: 14,
    shadowColor: '#000', shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15, shadowRadius: 10, elevation: 6,
  },
  appName: { fontSize: 22, fontWeight: '800', color: '#1A1A2E' },
  tagline: { fontSize: 13, color: '#888', marginTop: 3 },

  card: {
    backgroundColor: '#fff', borderRadius: 20, padding: 24,
    shadowColor: '#000', shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.08, shadowRadius: 12, elevation: 6,
  },

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

  successWrap: { flex: 1, justifyContent: 'center', alignItems: 'center', gap: 12, padding: 32 },
  successTitle: { fontSize: 24, fontWeight: '700', color: '#1A1A2E' },
  successSub:   { fontSize: 14, color: '#888', textAlign: 'center' },
});
