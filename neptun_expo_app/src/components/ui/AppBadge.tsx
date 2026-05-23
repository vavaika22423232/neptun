import { memo } from 'react';
import { StyleSheet, View } from 'react-native';
import { Text } from '../Text';
import { useThemedStyles } from '../../theme/useAppTheme';
import { fonts } from '../../theme/fonts';

type Props = {
  label: string;
  tone?: 'default' | 'accent' | 'success' | 'warning' | 'danger' | 'premium';
};

export const AppBadge = memo(function AppBadge({ label, tone = 'default' }: Props) {
  const styles = useThemedStyles((t) => {
    const bg =
      tone === 'accent'
        ? t.colors.primaryMuted
        : tone === 'success'
          ? t.colors.successMuted
          : tone === 'warning'
            ? t.colors.warningMuted
            : tone === 'danger'
              ? t.colors.dangerMuted
              : tone === 'premium'
                ? t.colors.proSoft
                : t.colors.surfaceHighlight;
    const fg =
      tone === 'accent'
        ? t.colors.primary
        : tone === 'success'
          ? t.colors.success
          : tone === 'warning'
            ? t.colors.warning
            : tone === 'danger'
              ? t.colors.danger
              : tone === 'premium'
                ? t.colors.pro
                : t.colors.textSecondary;

    return StyleSheet.create({
      pill: {
        paddingHorizontal: 8,
        paddingVertical: 3,
        borderRadius: t.radii.pill,
        backgroundColor: bg,
      },
      text: {
        fontFamily: fonts.bold,
        fontSize: 11,
        color: fg,
      },
    });
  });

  return (
    <View style={styles.pill}>
      <Text style={styles.text}>{label}</Text>
    </View>
  );
});
