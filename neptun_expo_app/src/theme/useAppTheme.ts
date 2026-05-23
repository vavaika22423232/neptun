import { useContext, useMemo } from 'react';
import { ThemeContext } from './ThemeContext';

export function useAppTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx.isReady) {
    return ctx;
  }
  return ctx;
}

export function useThemeColors() {
  return useAppTheme().theme.colors;
}

export function useLegacyPalette() {
  return useAppTheme().theme.palette;
}

export function useLegacyColors() {
  return useAppTheme().theme.legacyColors;
}

export function useRadarTheme() {
  return useAppTheme().theme.radar;
}

export function useChatTheme() {
  return useAppTheme().theme.chat;
}

export function useProfileTheme() {
  return useAppTheme().theme.profile;
}

export function useThemedStyles<T>(factory: (theme: ReturnType<typeof useAppTheme>['theme']) => T): T {
  const { theme } = useAppTheme();
  return useMemo(() => factory(theme), [theme, factory]);
}
