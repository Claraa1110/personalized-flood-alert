import { useState, useEffect, useCallback } from 'react';
import { View, ActivityIndicator, AppState } from 'react-native';
import * as Notifications from 'expo-notifications';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Ionicons } from '@expo/vector-icons';
import HomeScreen from '../screens/HomeScreen';
import PropertyListScreen from '../screens/PropertyListScreen';
import AlertScreen from '../screens/AlertScreen';
import SettingsScreen from '../screens/SettingsScreen';
import LoginScreen from '../screens/LoginScreen';
import RegisterScreen from '../screens/RegisterScreen';
import ForgotPasswordScreen from '../screens/ForgotPasswordScreen';
import { AuthProvider, useAuth } from '../context/AuthContext';
import { apiFetch } from '../lib/api';
import { registerForPushNotifications, updateBadgeCount } from '../lib/notifications';

const Tab = createBottomTabNavigator();

type IoniconsName = React.ComponentProps<typeof Ionicons>['name'];

const TAB_ICONS: Record<string, { active: IoniconsName; inactive: IoniconsName }> = {
  首頁: { active: 'home', inactive: 'home-outline' },
  列表: { active: 'list', inactive: 'list-outline' },
  警報: { active: 'notifications', inactive: 'notifications-outline' },
  設定: { active: 'settings', inactive: 'settings-outline' },
};

function MainTabs() {
  const [unreadCount, setUnreadCount] = useState(0);

  const fetchUnreadCount = useCallback(async () => {
    try {
      const resp = await apiFetch('/api/alerts');
      if (resp.ok) {
        const data = await resp.json();
        const list: any[] = data.alerts ?? data;
        setUnreadCount(list.filter((a: any) => !a.read_at).length);
      }
    } catch {}
  }, []);

  useEffect(() => { fetchUnreadCount(); }, []);

  const badgeValue = unreadCount === 0 ? undefined : unreadCount > 99 ? '99+' : unreadCount;

  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarIcon: ({ focused, color, size }) => {
          const icons = TAB_ICONS[route.name];
          const name = focused ? icons.active : icons.inactive;
          return <Ionicons name={name} size={size} color={color} />;
        },
        tabBarActiveTintColor: '#2E75B6',
        tabBarInactiveTintColor: '#999',
        headerShown: true,
      })}
      screenListeners={{ focus: () => fetchUnreadCount() }}
    >
      <Tab.Screen name="首頁" component={HomeScreen} />
      <Tab.Screen name="列表" component={PropertyListScreen} />
      <Tab.Screen
        name="警報"
        component={AlertScreen}
        options={{ tabBarBadge: badgeValue }}
      />
      <Tab.Screen name="設定" component={SettingsScreen} />
    </Tab.Navigator>
  );
}

function AuthStack() {
  const [screen, setScreen] = useState<'login' | 'register' | 'forgot'>('login');
  if (screen === 'register') return <RegisterScreen onGoLogin={() => setScreen('login')} />;
  if (screen === 'forgot')   return <ForgotPasswordScreen onGoLogin={() => setScreen('login')} />;
  return <LoginScreen onGoRegister={() => setScreen('register')} onGoForgot={() => setScreen('forgot')} />;
}

function RootNavigator() {
  const { session, loading } = useAuth();

  // 登入後：註冊推播 token + 更新 badge；登出後：清除 badge
  useEffect(() => {
    if (session) {
      registerForPushNotifications();
      updateBadgeCount();
    } else {
      Notifications.setBadgeCountAsync(0);
    }
  }, [session?.user?.id]);

  // App 從背景回到前景時更新 badge
  useEffect(() => {
    const sub = AppState.addEventListener('change', (state) => {
      if (state === 'active' && session) {
        updateBadgeCount();
      }
    });
    return () => sub.remove();
  }, [session]);

  if (loading) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#F0F4F8' }}>
        <ActivityIndicator size="large" color="#2E75B6" />
      </View>
    );
  }

  return (
    <NavigationContainer>
      {session ? <MainTabs /> : <AuthStack />}
    </NavigationContainer>
  );
}

export default function AppNavigator() {
  return (
    <AuthProvider>
      <RootNavigator />
    </AuthProvider>
  );
}
