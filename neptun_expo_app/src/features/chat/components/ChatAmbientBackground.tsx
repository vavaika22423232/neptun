import { StyleSheet, View } from 'react-native';
import { useAppTheme } from '../../../theme/useAppTheme';

/** Flat messenger background — pure black in dark mode. */
export function ChatAmbientBackground() {
  const { theme } = useAppTheme();

  return (
    <View
      style={[StyleSheet.absoluteFill, { backgroundColor: theme.chat.bg }]}
      pointerEvents="none"
    />
  );
}
