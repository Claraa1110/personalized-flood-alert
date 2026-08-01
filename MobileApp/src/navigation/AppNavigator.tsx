import { useState, useEffect, useCallback } from 'react';
import { View, ActivityIndicator } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Ionicons } from '@expo/vector-icons';
import HomeScreen from '../screens/HomeScreen';
import PropertyListScreen from '../screens/PropertyListScreen';
import AlertScreen from '../screens/AlertScreen';
import SettingsScreen from '../screens/SettingsScreen';
import LoginScreen from '../screens/LoginScreen';
import RegisterScreen from '../screens/RegisterScreen';
import { AuthProvider, useAuth } from '../context/AuthContext';
import { apiFetch } from '../lib/api';
import { registerForPushNotifications } from '../lib/notifications';

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
  const [screen, setScreen] = useState<'login' | 'register'>('login');
  return screen === 'login'
    ? <LoginScreen onGoRegister={() => setScreen('register')} />
    : <RegisterScreen onGoLogin={() => setScreen('login')} />;
}

function RootNavigator() {
  const { session, loading } = useAuth();

  // 登入後自動取得並註冊推播 token
  useEffect(() => {
    if (session) {
      registerForPushNotifications();
    }
  }, [session?.user?.id]);

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
