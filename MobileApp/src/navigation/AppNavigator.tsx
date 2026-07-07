import { useState, useEffect, useCallback } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Ionicons } from '@expo/vector-icons';
import HomeScreen from '../screens/HomeScreen';
import PropertyListScreen from '../screens/PropertyListScreen';
import AlertScreen from '../screens/AlertScreen';
import SettingsScreen from '../screens/SettingsScreen';

const Tab = createBottomTabNavigator();

type IoniconsName = React.ComponentProps<typeof Ionicons>['name'];

const TAB_ICONS: Record<string, { active: IoniconsName; inactive: IoniconsName }> = {
  首頁: { active: 'home', inactive: 'home-outline' },
  列表: { active: 'list', inactive: 'list-outline' },
  警報: { active: 'notifications', inactive: 'notifications-outline' },
  設定: { active: 'settings', inactive: 'settings-outline' },
};

export default function AppNavigator() {
  const [unreadCount, setUnreadCount] = useState(0);
  const base = process.env.EXPO_PUBLIC_API_URL;

  const fetchUnreadCount = useCallback(async () => {
    try {
      const resp = await fetch(`${base}/api/alerts`);
      if (resp.ok) {
        const data = await resp.json();
        const list: any[] = data.alerts ?? data;
        const count = list.filter((a: any) => !a.read_at).length;
        setUnreadCount(count);
      }
    } catch {}
  }, []);

  useEffect(() => { fetchUnreadCount(); }, []);

  const badgeValue = unreadCount === 0 ? undefined : unreadCount > 99 ? '99+' : unreadCount;

  return (
    <NavigationContainer>
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
    </NavigationContainer>
  );
}
