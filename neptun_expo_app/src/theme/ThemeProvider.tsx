import { useCallback, useMemo, useState } from 'react';
import { Appearance, useColorScheme } from 'react-native';
import { ThemeContext, type ThemeContextValue } from './ThemeContext';
import { setActiveTheme } from './activeTheme';
import { createAppTheme } from './theme';
import { loadThemeMode, saveThemeMode } from './themeStorage';
import type { ResolvedScheme, ThemeMode } from './types';

function resolveScheme(mode: ThemeMode, system: string | null | undefined): ResolvedScheme {
  if (mode === 'light') return 'light';
  if (mode === 'dark') return 'dark';
  return system === 'light' ? 'light' : 'dark';
}

type Props = {
  children: React.ReactNode;
};

export function ThemeProvider({ children }: Props) {
  const systemScheme = useColorScheme();
  const [mode, setModeState] = useState<ThemeMode>(() => loadThemeMode());

  const setMode = useCallback((next: ThemeMode) => {
    setModeState(next);
    saveThemeMode(next);
  }, []);

  const scheme = resolveScheme(mode, systemScheme ?? Appearance.getColorScheme());
  const theme = useMemo(() => {
    const next = createAppTheme(scheme);
    setActiveTheme(next);
    return next;
  }, [scheme]);

  const value = useMemo<ThemeContextValue>(
    () => ({
      theme,
      mode,
      setMode,
      isReady: true,
    }),
    [theme, mode, setMode],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}
