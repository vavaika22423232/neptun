import * as Notifications from 'expo-notifications';
import {
  PlusJakartaSans_400Regular,
  PlusJakartaSans_500Medium,
  PlusJakartaSans_600SemiBold,
  PlusJakartaSans_700Bold,
} from '@expo-google-fonts/plus-jakarta-sans';
import { NavigationContainer, DarkTheme } from '@react-navigation/native';
import { useFonts } from 'expo-font';
import { StatusBar } from 'expo-status-bar';
import { useCallback, useEffect, useRef, useState } from 'react';
import { View } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { AppProvider } from './src/context/AppContext';
import { AppNavigator } from './src/navigation/AppNavigator';
import { AppUpdateRequiredScreen } from './src/screens/AppUpdateRequiredScreen';
import {
  appVersionGateService,
  type AppUpdateBlockPayload,
} from './src/services/appVersionGateService';
import { colors } from './src/theme/colors';
import { shouldBlockSleepNotification } from './src/services/sleepModeStore';

Notifications.setNotificationHandler({
  handleNotification: async (notification) => {
    const title = notification.request.content.title ?? '';
    const body = notification.request.content.body ?? '';
    const blocked = shouldBlockSleepNotification(`${title}\n${body}`);
    return {
      shouldShowBanner: !blocked,
      shouldShowList: !blocked,
      shouldPlaySound: !blocked,
      shouldSetBadge: true,
    };
  },
});

const navigationTheme = {
  ...DarkTheme,
  colors: {
    ...DarkTheme.colors,
    background: colors.bg,
    card: colors.surface,
    border: colors.border,
    primary: colors.accent,
    text: colors.text,
    notification: colors.accent,
  },
};

export default function App() {
  const [fontsLoaded, fontError] = useFonts({
    PlusJakartaSans_400Regular,
    PlusJakartaSans_500Medium,
    PlusJakartaSans_600SemiBold,
    PlusJakartaSans_700Bold,
  });
  const fontsReady = fontsLoaded || fontError != null;

  const [versionGate, setVersionGate] = useState<
    'checking' | 'ok' | { blocked: AppUpdateBlockPayload }
  >('checking');
  const gateAbortRef = useRef<AbortController | null>(null);

  const runGate = useCallback(() => {
    gateAbortRef.current?.abort();
    const ac = new AbortController();
    gateAbortRef.current = ac;
    setVersionGate('checking');
    appVersionGateService.evaluate(ac.signal).then((r) => {
      if (ac.signal.aborted) return;
      if (r.ok) setVersionGate('ok');
      else setVersionGate({ blocked: r.block });
    });
  }, []);

  useEffect(() => {
    runGate();
    return () => {
      gateAbortRef.current?.abort();
    };
  }, [runGate]);

  const booting = versionGate === 'checking' || !fontsReady;

  return (
    <SafeAreaProvider>
      {booting ? (
        <View style={{ flex: 1, backgroundColor: colors.bg }} />
      ) : versionGate === 'ok' ? (
        <AppProvider>
          <NavigationContainer theme={navigationTheme}>
            <StatusBar style="light" />
            <AppNavigator />
          </NavigationContainer>
        </AppProvider>
      ) : (
        <AppUpdateRequiredScreen
          payload={versionGate.blocked}
          onRetry={() => {
            void runGate();
          }}
        />
      )}
    </SafeAreaProvider>
  );
}
