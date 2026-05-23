import { createContext } from 'react';
import type { AppTheme, ThemeMode } from './types';
import { darkAppTheme } from './theme';

export type ThemeContextValue = {
  theme: AppTheme;
  mode: ThemeMode;
  setMode: (mode: ThemeMode) => void;
  isReady: boolean;
};

export const ThemeContext = createContext<ThemeContextValue>({
  theme: darkAppTheme,
  mode: 'dark',
  setMode: () => {},
  isReady: false,
});
