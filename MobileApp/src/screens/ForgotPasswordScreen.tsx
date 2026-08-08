import { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  ActivityIndicator, KeyboardAvoidingView, Platform, ScrollView, Image,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { supabase } from '../lib/supabase';

const RESET_REDIRECT_URL = 'https://ff-weathered-paper-9628.fly.dev/reset-password';

interface Props {
  onGoLogin: () => void;
}

export default function ForgotPasswordScreen({ onGoLogin }: Props) {
  const [email, setEmail]     = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState<string | null>(null);
  const [sent, setSent]       = useState(false);

  const handleSend = async () => {
    if (!email.trim()) { setError('請輸入電子郵件'); return; }
    setLoading(true);
    setError(null);
    try {
      const { error: e } = await supabase.auth.resetPasswordForEmail(email.trim(), {
        redirectTo: RESET_REDIRECT_URL,
      });
      if (e) {
        const msg = e.message.toLowerCase();
        if (msg.includes('network') || msg.includes('fetch') || msg.includes('connect')) {
          setError('網路連線失敗，請確認網路後再試');
        } else {
          setError(e.message);
        }
        return;
      }
      setSent(true);
    } catch (err: any) {
      setError('網路連線失敗，請確認網路後再試');
    } finally {
      setLoading(false);
    }
  };

  if (sent) {
    return (
      <View style={styles.root}>
        <View style={styles.successWrap}>
          <Ionicons name="mail-outline" size={64} color="#2E75B6" />
          <Text style={styles.successTitle}>重設信已寄出</Text>
          <Text style={styles.successSub}>
            請查收 {email} 的信箱，點擊信中連結即可重設密碼
          </Text>
          <TouchableOpacity style={styles.btn} onPress={onGoLogin}>
            <Text style={styles.btnText}>返回登入</Text>
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
          <Text style={styles.tagline}>重設你的密碼</Text>
        </View>

        <View style={styles.card}>
          <Text style={styles.title}>忘記密碼</Text>
          <Text style={styles.hint}>
            輸入你的帳號電子郵件，我們將寄送密碼重設連結給你
          </Text>

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

          {error ? (
            <View style={styles.errorBox}>
              <Ionicons name="alert-circle-outline" size={14} color="#C00000" />
              <Text style={styles.errorText}>{error}</Text>
            </View>
          ) : null}

          <TouchableOpacity style={styles.btn} onPress={handleSend} disabled={loading}>
            {loading
              ? <ActivityIndicator color="#fff" />
              : <Text style={styles.btnText}>寄送重設信</Text>}
          </TouchableOpacity>
        </View>

        <TouchableOpacity style={styles.backRow} onPress={onGoLogin}>
          <Ionicons name="arrow-back-outline" size={16} color="#2E75B6" />
          <Text style={styles.backLink}>返回登入</Text>
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
  title: { fontSize: 22, fontWeight: '700', color: '#1A1A2E', marginBottom: 8, textAlign: 'center' },
  hint:  { fontSize: 13, color: '#888', textAlign: 'center', lineHeight: 18, marginBottom: 4 },

  label: { fontSize: 13, fontWeight: '600', color: '#555', marginBottom: 6, marginTop: 16 },
  input: {
    borderWidth: 1.5, borderColor: '#E0E0E0', borderRadius: 12,
    paddingHorizontal: 14, paddingVertical: 12, fontSize: 15,
    color: '#222', backgroundColor: '#FAFAFA',
  },

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

  backRow: { flexDirection: 'row', justifyContent: 'center', alignItems: 'center', marginTop: 24, gap: 4 },
  backLink: { fontSize: 14, color: '#2E75B6', fontWeight: '700' },

  successWrap: { flex: 1, justifyContent: 'center', alignItems: 'center', gap: 16, padding: 32 },
  successTitle: { fontSize: 22, fontWeight: '700', color: '#1A1A2E' },
  successSub:   { fontSize: 14, color: '#888', textAlign: 'center', lineHeight: 20 },
});
