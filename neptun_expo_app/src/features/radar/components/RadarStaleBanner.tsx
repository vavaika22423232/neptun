import { Ionicons } from '@expo/vector-icons';
import { StyleSheet, View } from 'react-native';
import { Text } from '../../../components/Text';
import { fonts } from '../../../theme/fonts';
import { useThemedStyles } from '../../../theme/useAppTheme';

export function RadarStaleBanner() {
  const styles = useStaleStyles();

  return (
    <View style={styles.root}>
      <Ionicons name="cloud-offline-outline" size={16} color={styles.mutedColor.color} />
      <Text style={styles.label}>Показано збережені дані</Text>
    </View>
  );
}

function useStaleStyles() {
  return useThemedStyles((t) => {
    const isDark = t.scheme === 'dark';
    return StyleSheet.create({
      root: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        paddingHorizontal: 14,
        paddingVertical: 10,
        borderRadius: 14,
        backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : '#FFFFFF',
      },
      label: {
        flex: 1,
        fontFamily: fonts.medium,
        fontSize: 13,
        color: t.colors.textSecondary,
      },
      mutedColor: { color: t.colors.textMuted },
    });
  });
}
