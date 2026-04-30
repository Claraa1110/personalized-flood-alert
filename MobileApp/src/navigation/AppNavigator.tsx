import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import PropertyScreen from '../screens/PropertyScreen';
import AlertScreen from '../screens/AlertScreen';
import SettingsScreen from '../screens/SettingsScreen';

const Tab = createBottomTabNavigator();

export default function AppNavigator() {
  return (
    <NavigationContainer>
      <Tab.Navigator>
        <Tab.Screen name="財產總覽" component={PropertyScreen} />
        <Tab.Screen name="警報" component={AlertScreen} />
        <Tab.Screen name="設定" component={SettingsScreen} />
      </Tab.Navigator>
    </NavigationContainer>
  );
}
