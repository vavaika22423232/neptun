import { StyleSheet, View } from 'react-native';
import { Text } from '../../../components/Text';
import { fonts } from '../../../theme/fonts';
import { useThemedStyles } from '../../../theme/useAppTheme';

export function ChatDateDivider({ label }: { label: string }) {
  const styles = useDateStyles();

  return (
    <View style={styles.wrap}>
      <View style={styles.pill}>
        <Text style={styles.label}>{label}</Text>
      </View>
    </View>
  );
}

function useDateStyles() {
  return useThemedStyles((t) => {
    const isDark = t.scheme === 'dark';
    return StyleSheet.create({
      wrap: {
        alignItems: 'center',
        marginVertical: 14,
      },
      pill: {
        paddingHorizontal: 12,
        paddingVertical: 5,
        borderRadius: 12,
        backgroundColor: isDark ? 'rgba(255,255,255,0.10)' : 'rgba(0,0,0,0.06)',
      },
      label: {
        fontFamily: fonts.medium,
        fontSize: 11,
        color: isDark ? 'rgba(235,235,245,0.72)' : t.colors.textMuted,
      },
    });
  });
}
