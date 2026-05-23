import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useMemo } from 'react';
import { useAppTheme } from '../theme/useAppTheme';
import { fonts } from '../theme/fonts';

export function ThemedNavigation() {
  const { theme } = useAppTheme();
  const c = theme.colors;

  const screenOptions = useMemo(
    () => ({
      headerStyle: { backgroundColor: c.background },
      headerTintColor: c.textPrimary,
      headerShadowVisible: false,
      headerTitleStyle: { fontFamily: fonts.semiBold, fontSize: 17, color: c.textPrimary },
      contentStyle: { backgroundColor: c.background },
      animation: 'fade_from_bottom' as const,
    }),
    [c.background, c.textPrimary],
  );

  return (
    <>
      <StatusBar style={c.statusBarStyle} />
      <Stack screenOptions={screenOptions}>
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen name="onboarding" options={{ headerShown: false }} />
        <Stack.Screen name="premium" options={{ headerShown: false, presentation: 'modal' }} />
        <Stack.Screen name="history" options={{ title: 'Історія тривог' }} />
        <Stack.Screen name="analytics" options={{ title: 'Аналітика' }} />
        <Stack.Screen name="heatmap" options={{ title: 'Теплова карта тривог' }} />
        <Stack.Screen name="sleep-mode" options={{ title: 'Режим сну' }} />
        <Stack.Screen name="chat-admin" options={{ title: 'Модерація чату' }} />
        <Stack.Screen name="chat-settings" options={{ headerShown: false }} />
        <Stack.Screen name="complaints" options={{ title: 'Скарги чату' }} />
        <Stack.Screen name="web-embed" options={{ title: 'NEPTUN' }} />
        <Stack.Screen name="radar-full" options={{ title: 'Радар загроз' }} />
        <Stack.Screen name="trust" options={{ title: 'Надійність' }} />
        <Stack.Screen name="feedback" options={{ title: "Зворотній зв'язок" }} />
        <Stack.Screen name="feedback-moderation" options={{ title: 'Модерація відгуків' }} />
        <Stack.Screen name="admin" options={{ title: 'Адмін панель' }} />
        <Stack.Screen name="safety" options={{ title: 'Центр безпеки' }} />
        <Stack.Screen name="shelters" options={{ title: 'Укриття поруч' }} />
        <Stack.Screen name="briefing" options={{ title: 'Брифінг', presentation: 'modal' }} />
      </Stack>
    </>
  );
}
