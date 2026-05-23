import { Ionicons } from '@expo/vector-icons';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { useEffect, useState } from 'react';
import { View } from 'react-native';
import { NeptunTabBar } from '../components/NeptunTabBar';
import { fonts } from '../theme/fonts';
import { useLegacyColors } from '../theme/useAppTheme';
import { AlarmHistoryScreen } from '../screens/AlarmHistoryScreen';
import { ChatAdminScreen } from '../screens/ChatAdminScreen';
import { ComplaintsScreen } from '../screens/ComplaintsScreen';
import { ChatConversationScreen } from '../screens/ChatConversationScreen';
import { HeatmapScreen } from '../screens/HeatmapScreen';
import { MapScreen } from '../screens/MapScreen';
import { OnboardingScreen } from '../screens/OnboardingScreen';
import { PersonalAnalyticsScreen } from '../screens/PersonalAnalyticsScreen';
import { PremiumScreen } from '../screens/PremiumScreen';
import { ProfileScreen } from '../screens/ProfileScreen';
import { RadarScreen } from '../screens/RadarScreen';
import { RegionsScreen } from '../screens/RegionsScreen';
import { SleepModeScreen } from '../screens/SleepModeScreen';
import { WebEmbedScreen } from '../screens/WebEmbedScreen';
import { storage } from '../services/storage';
import { MainTabParamList, RootStackParamList } from './types';

const Stack = createNativeStackNavigator<RootStackParamList>();
const Tabs = createBottomTabNavigator<MainTabParamList>();

function MainTabs() {
  return (
    <Tabs.Navigator
      tabBar={(props) => <NeptunTabBar {...props} />}
      screenOptions={{
        headerShown: false,
      }}
    >
      <Tabs.Screen name="Map" component={MapScreen} options={{ title: 'Карта', tabBarLabel: 'Карта' }} />
      <Tabs.Screen name="Radar" component={RadarScreen} options={{ title: 'Радар', tabBarLabel: 'Радар' }} />
      <Tabs.Screen
        name="Regions"
        component={RegionsScreen}
        options={{ title: 'Регіони', tabBarLabel: 'Регіони' }}
      />
      <Tabs.Screen name="Chat" component={ChatConversationScreen} options={{ title: 'Чат', tabBarLabel: 'Чат' }} />
      <Tabs.Screen
        name="Profile"
        component={ProfileScreen}
        options={{ title: 'Профіль', tabBarLabel: 'Профіль' }}
      />
    </Tabs.Navigator>
  );
}

export function AppNavigator() {
  const c = useLegacyColors();
  const [gate, setGate] = useState<'loading' | 'onboarding' | 'main'>('loading');

  useEffect(() => {
    void storage.getIsFirstLaunch().then((first) => setGate(first ? 'onboarding' : 'main'));
  }, []);

  if (gate === 'loading') {
    return <View style={{ flex: 1, backgroundColor: c.bg }} />;
  }

  return (
    <Stack.Navigator
      initialRouteName={gate === 'onboarding' ? 'Onboarding' : 'MainTabs'}
      screenOptions={{
        headerStyle: { backgroundColor: c.bg },
        headerTintColor: c.text,
        headerTitleStyle: { fontFamily: fonts.semiBold, fontSize: 18, color: c.text },
        headerShadowVisible: false,
        contentStyle: { backgroundColor: c.bg },
      }}
    >
      <Stack.Screen
        name="Onboarding"
        component={OnboardingScreen}
        options={{ headerShown: false }}
      />
      <Stack.Screen name="MainTabs" component={MainTabs} options={{ headerShown: false }} />
      <Stack.Screen name="Premium" component={PremiumScreen} options={{ headerShown: false }} />
      <Stack.Screen
        name="AlarmHistory"
        component={AlarmHistoryScreen}
        options={{ title: 'Історія тривог' }}
      />
      <Stack.Screen
        name="PersonalAnalytics"
        component={PersonalAnalyticsScreen}
        options={{ title: 'Аналітика' }}
      />
      <Stack.Screen name="Heatmap" component={HeatmapScreen} options={{ title: 'Теплова карта' }} />
      <Stack.Screen name="SleepMode" component={SleepModeScreen} options={{ title: 'Режим сну' }} />
      <Stack.Screen
        name="ChatAdmin"
        component={ChatAdminScreen}
        options={{ title: 'Модерація чату' }}
      />
      <Stack.Screen name="Complaints" component={ComplaintsScreen} options={{ title: 'Скарги чату' }} />
      <Stack.Screen
        name="WebEmbed"
        component={WebEmbedScreen}
        options={({ route }) => ({
          title: route.params.title ?? 'NEPTUN',
        })}
      />
    </Stack.Navigator>
  );
}
