import { memo } from 'react';
import { StyleSheet, View } from 'react-native';
import { Text } from '../../../../components/Text';
import { fonts } from '../../../../theme/fonts';
import { useThemedStyles } from '../../../../theme/useAppTheme';

type Props = {
  label?: string;
};

function isProLabel(label: string): boolean {
  const u = label.toUpperCase();
  return u === 'PRO' || u.includes('PRO') || u === 'FREE';
}

function ProBadgeInner({ label = 'PRO' }: Props) {
  const pro = isProLabel(label) && label.toUpperCase() !== 'FREE';
  const isFree = label.toUpperCase() === 'FREE';
  const styles = useBadgeStyles(pro, isFree);

  return (
    <View style={styles.wrap}>
      <Text style={styles.text}>{label}</Text>
    </View>
  );
}

function useBadgeStyles(pro: boolean, isFree: boolean) {
  return useThemedStyles((t) =>
    StyleSheet.create({
      wrap: {
        paddingHorizontal: 8,
        paddingVertical: 3,
        borderRadius: 6,
        backgroundColor: pro
          ? t.colors.proSoft
          : isFree
            ? t.colors.surfaceHighlight
            : t.colors.surfaceSoft,
        borderWidth: pro ? StyleSheet.hairlineWidth : 0,
        borderColor: pro ? 'rgba(255,204,0,0.35)' : 'transparent',
      },
      text: {
        fontFamily: fonts.bold,
        fontSize: 11,
        letterSpacing: 0.3,
        color: pro ? t.colors.pro : isFree ? t.colors.textMuted : t.colors.textSecondary,
      },
    }),
  );
}

export const ProBadge = memo(ProBadgeInner);
