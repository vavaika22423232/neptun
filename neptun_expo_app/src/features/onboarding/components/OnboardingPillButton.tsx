import { ActivityIndicator, StyleSheet } from 'react-native';
import { NeptunPressable } from '../../../design/components/NeptunPressable';
import { Text } from '../../../components/Text';
import { fonts } from '../../../theme/fonts';

type Props = {
  label: string;
  onPress: () => void;
  disabled?: boolean;
  loading?: boolean;
  variant?: 'primary' | 'secondary';
};

/** Black iOS-style pill CTA with soft shadow. */
export function OnboardingPillButton({
  label,
  onPress,
  disabled,
  loading,
  variant = 'primary',
}: Props) {
  const isPrimary = variant === 'primary';

  return (
    <NeptunPressable
      haptic={!disabled && !loading}
      disabled={disabled || loading}
      onPress={onPress}
      style={[
        styles.root,
        isPrimary ? styles.primary : styles.secondary,
        (disabled || loading) && styles.disabled,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={isPrimary ? '#FFFFFF' : '#000000'} />
      ) : (
        <Text style={[styles.label, !isPrimary && styles.labelSecondary]}>{label}</Text>
      )}
    </NeptunPressable>
  );
}

const styles = StyleSheet.create({
  root: {
    minHeight: 56,
    paddingHorizontal: 28,
    borderRadius: 28,
    alignItems: 'center',
    justifyContent: 'center',
  },
  primary: {
    backgroundColor: '#000000',
    shadowColor: '#000000',
    shadowOpacity: 0.18,
    shadowRadius: 20,
    shadowOffset: { width: 0, height: 10 },
    elevation: 10,
  },
  secondary: {
    backgroundColor: '#FFFFFF',
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: 'rgba(60,60,67,0.18)',
  },
  disabled: { opacity: 0.55 },
  label: {
    fontFamily: fonts.semiBold,
    fontSize: 17,
    color: '#FFFFFF',
    letterSpacing: -0.2,
  },
  labelSecondary: {
    color: '#000000',
  },
});
