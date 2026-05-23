import { memo } from 'react';
import { StyleSheet, View } from 'react-native';
import { Text } from '../Text';
import { useThemedStyles } from '../../theme/useAppTheme';
import { fonts } from '../../theme/fonts';

type Props = {
  label: string;
  tone?: 'default' | 'live' | 'warning' | 'muted';
};

export const HeaderStatusBadge = memo(function HeaderStatusBadge({
  label,
  tone = 'default',
}: Props) {
  const styles = useThemedStyles((t) =>
    StyleSheet.create({
      pill: {
        paddingHorizontal: 10,
        paddingVertical: 4,
        borderRadius: t.radii.pill,
        borderWidth: StyleSheet.hairlineWidth,
        backgroundColor:
          tone === 'live'
            ? t.colors.successMuted
            : tone === 'warning'
              ? t.colors.warningMuted
              : t.colors.surfaceHighlight,
        borderColor:
          tone === 'live'
            ? 'rgba(52, 211, 153, 0.25)'
            : tone === 'warning'
              ? 'rgba(251, 191, 36, 0.25)'
              : t.colors.border,
      },
      text: {
        fontFamily: fonts.semiBold,
        fontSize: 12,
        color:
          tone === 'live'
            ? t.colors.success
            : tone === 'warning'
              ? t.colors.warning
              : tone === 'muted'
                ? t.colors.textMuted
                : t.colors.textSecondary,
      },
    }),
  );

  return (
    <View style={styles.pill}>
      <Text style={styles.text}>{label}</Text>
    </View>
  );
});
