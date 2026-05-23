import { ActivityIndicator, StyleSheet, View } from 'react-native';
import { Text } from '../Text';
import { useAppTheme, useThemedStyles } from '../../theme/useAppTheme';
import { fonts } from '../../theme/fonts';

type Props = {
  label?: string;
};

export function AppLoadingState({ label = 'Завантаження…' }: Props) {
  const { theme } = useAppTheme();
  const styles = useThemedStyles((t) =>
    StyleSheet.create({
      root: {
        flex: 1,
        alignItems: 'center',
        justifyContent: 'center',
        gap: t.spacing.md,
        padding: t.spacing.xl,
      },
      label: {
        fontFamily: fonts.medium,
        fontSize: 15,
        color: t.colors.textSecondary,
      },
    }),
  );

  return (
    <View style={styles.root}>
      <ActivityIndicator size="large" color={theme.colors.primary} />
      <Text style={styles.label}>{label}</Text>
    </View>
  );
}
