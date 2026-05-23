import 'react-native-gesture-handler';
import { PlusJakartaSans_400Regular, PlusJakartaSans_500Medium, PlusJakartaSans_600SemiBold, PlusJakartaSans_700Bold } from '@expo-google-fonts/plus-jakarta-sans';
import { useFonts } from 'expo-font';
import { useCallback, useEffect, useRef, useState } from 'react';
import { View } from 'react-native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppBootstrapGate } from '../src/components/AppBootstrapGate';
import { AppErrorBoundary } from '../src/components/AppErrorBoundary';
import { AppProvider } from '../src/context/AppContext';
import { AppUpdateRequiredScreen } from '../src/screens/AppUpdateRequiredScreen';
import { appVersionGateService, type AppUpdateBlockPayload } from '../src/services/appVersionGateService';
import { notificationService } from '../src/services/notificationService';
import { hydrateSleepMode } from '../src/services/sleepModeStore';
import { NeptunBootSplash } from '../src/design/components/NeptunBootSplash';
import { ThemedNavigation } from '../src/components/ThemedNavigation';
import { ThemeProvider } from '../src/theme/ThemeProvider';

notificationService.configureForegroundHandler();

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 15000,
      gcTime: 5 * 60 * 1000,
      retry: 1,
    },
  },
});

export default function RootLayout() {
  const [fontsLoaded, fontError] = useFonts({
    PlusJakartaSans_400Regular,
    PlusJakartaSans_500Medium,
    PlusJakartaSans_600SemiBold,
    PlusJakartaSans_700Bold,
  });
  const [versionGate, setVersionGate] = useState<'checking' | 'ok' | { blocked: AppUpdateBlockPayload }>('checking');
  const gateAbortRef = useRef<AbortController | null>(null);

  const runGate = useCallback(() => {
    gateAbortRef.current?.abort();
    const ac = new AbortController();
    gateAbortRef.current = ac;
    setVersionGate('checking');
    appVersionGateService.evaluate(ac.signal).then((result) => {
      if (ac.signal.aborted) return;
      setVersionGate(result.ok ? 'ok' : { blocked: result.block });
    });
  }, []);

  useEffect(() => {
    void hydrateSleepMode();
    runGate();
    return () => gateAbortRef.current?.abort();
  }, [runGate]);

  const booting = versionGate === 'checking' || (!fontsLoaded && fontError == null);

  if (booting) return <NeptunBootSplash />;
  if (versionGate !== 'ok') {
    return <AppUpdateRequiredScreen payload={versionGate.blocked} onRetry={runGate} />;
  }

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <QueryClientProvider client={queryClient}>
          <ThemeProvider>
            <AppErrorBoundary>
              <AppProvider>
                <AppBootstrapGate>
                  <ThemedNavigation />
                </AppBootstrapGate>
              </AppProvider>
            </AppErrorBoundary>
          </ThemeProvider>
        </QueryClientProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
