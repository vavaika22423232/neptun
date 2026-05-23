import { StyleSheet } from 'react-native';
import type { LegacyColors } from './types';
import { useThemedStyles } from './useAppTheme';

/** Theme-aware StyleSheet for screens still on legacy color tokens. */
export function useLegacyScreenStyles<T extends StyleSheet.NamedStyles<T>>(
  factory: (colors: LegacyColors) => T,
): T {
  return useThemedStyles((theme) => StyleSheet.create(factory(theme.legacyColors)));
}
