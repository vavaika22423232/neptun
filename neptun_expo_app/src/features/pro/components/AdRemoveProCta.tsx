import { memo } from 'react';
import { StyleSheet } from 'react-native';
import { Text } from '../../../components/Text';
import { NeptunPressable } from '../../../design/components/NeptunPressable';
import { useThemedStyles } from '../../../theme/useAppTheme';
import { fonts } from '../../../theme/fonts';
import { useProAccess } from '../hooks/useProAccess';

function AdRemoveProCtaInner() {
  const { isPaid, openPaywall } = useProAccess();
  const styles = useAdRemoveStyles();

  if (isPaid) {
    return null;
  }

  return (
    <NeptunPressable
      haptic
      scaleTo={0.99}
      style={styles.row}
      onPress={() => openPaywall({ source: 'ads', lockedFeature: 'remove_ads' })}
      accessibilityLabel="Прибрати рекламу з PRO"
    >
      <Text style={styles.text}>Прибрати рекламу</Text>
      <Text style={styles.hint}>з PRO</Text>
    </NeptunPressable>
  );
}

function useAdRemoveStyles() {
  return useThemedStyles((t) =>
    StyleSheet.create({
      row: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 6,
        marginHorizontal: 16,
        marginBottom: 4,
        paddingVertical: 8,
      },
      text: {
        fontFamily: fonts.semiBold,
        fontSize: 13,
        color: t.colors.primary,
      },
      hint: {
        fontFamily: fonts.medium,
        fontSize: 12,
        color: t.colors.textMuted,
      },
    }),
  );
}

export const AdRemoveProCta = memo(AdRemoveProCtaInner);
