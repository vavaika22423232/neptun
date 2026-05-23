import { StyleSheet } from 'react-native';
import { Text } from '../../components/Text';
import { radii, typography } from '../tokens';
import { fonts } from '../../theme/fonts';
import { useThemedStyles } from '../../theme/useAppTheme';
import { NeptunPressable } from './NeptunPressable';

type Props = {
  label: string;
  active?: boolean;
  onPress?: () => void;
};

export function NeptunFilterPill({ label, active, onPress }: Props) {
  const styles = useThemedStyles((t) =>
    StyleSheet.create({
      pill: {
        borderRadius: radii.sm,
        paddingHorizontal: 10,
        paddingVertical: 5,
        backgroundColor: t.colors.surfaceSoft,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: t.colors.border,
      },
      pillOn: {
        backgroundColor: t.colors.primaryMuted,
        borderColor: t.colors.primary,
      },
      text: {
        fontFamily: fonts.medium,
        ...typography.bodySmall,
        color: t.colors.textSecondary,
      },
      textOn: {
        fontFamily: fonts.semiBold,
        color: t.colors.primary,
      },
    }),
  );

  return (
    <NeptunPressable haptic onPress={onPress} style={[styles.pill, active && styles.pillOn]}>
      <Text style={[styles.text, active && styles.textOn]}>{label}</Text>
    </NeptunPressable>
  );
}
