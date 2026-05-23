import { Tabs } from 'expo-router';
import type { BottomTabBarProps } from '@react-navigation/bottom-tabs';
import type { ReactNode } from 'react';
import { View, type StyleProp, type ViewStyle } from 'react-native';
import { AdBannerSlot } from '../../src/components/AdBannerSlot';
import { ChatTabChrome } from '../../src/components/ChatTabChrome';
import { ProfileTabChrome } from '../../src/components/ProfileTabChrome';
import { RegionsTabChrome } from '../../src/components/RegionsTabChrome';
import { BottomNavigationBar } from '../../src/components/BottomNavigationBar';
import { RadarTabChrome } from '../../src/features/radar/components/RadarTabChrome';
import { useAppTheme } from '../../src/theme/useAppTheme';

function tabHeader(routeName: string): ReactNode | undefined {
  switch (routeName) {
    case 'radar':
      return <RadarTabChrome />;
    case 'regions':
      return <RegionsTabChrome />;
    case 'chat':
      return <ChatTabChrome />;
    case 'profile':
      return <ProfileTabChrome />;
    default:
      return undefined;
  }
}

export default function TabsLayout() {
  const { theme } = useAppTheme();
  return (
    <Tabs
      screenOptions={({ route }) => {
        const header = tabHeader(route.name);
        return {
          headerShown: header != null,
          header: header ? () => header : undefined,
          tabBarStyle: {
            position: 'absolute',
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'transparent',
            borderTopWidth: 0,
            elevation: 0,
          },
          sceneStyle: {
            flex: 1,
            backgroundColor:
              route.name === 'chat'
                ? theme.chat.bg
                : route.name === 'radar' || route.name === 'profile' || route.name === 'regions'
                  ? theme.colors.cardMuted
                  : theme.colors.background,
          },
        };
      }}
      tabBar={(props: BottomTabBarProps & { style?: StyleProp<ViewStyle> }) => {
        const { style, ...rest } = props;
        return (
          <View pointerEvents="box-none" style={[style, { backgroundColor: 'transparent' }]}>
            <AdBannerSlot />
            <BottomNavigationBar {...rest} />
          </View>
        );
      }}
    >
      <Tabs.Screen name="index" options={{ title: 'Карта', headerShown: false }} />
      <Tabs.Screen name="radar" options={{ title: 'Радар' }} />
      <Tabs.Screen name="regions" options={{ href: null, title: 'Регіони' }} />
      <Tabs.Screen name="chat" options={{ title: 'Чат' }} />
      <Tabs.Screen name="profile" options={{ title: 'Профіль' }} />
    </Tabs>
  );
}
