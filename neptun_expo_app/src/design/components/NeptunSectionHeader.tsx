import { StyleSheet, View } from 'react-native';
import { Text } from '../../components/Text';
import { spacing, typography } from '../tokens';
import { fonts } from '../../theme/fonts';
import { useThemedStyles } from '../../theme/useAppTheme';

type Props = {
  title: string;
  subtitle?: string;
};

export function NeptunSectionHeader({ title, subtitle }: Props) {
  const styles = useThemedStyles((t) =>
    StyleSheet.create({
      root: { gap: 4, marginBottom: spacing.xs },
      title: {
        fontFamily: fonts.bold,
        ...typography.caption,
        color: t.colors.textFaint,
        letterSpacing: 0.8,
        textTransform: 'uppercase',
      },
      subtitle: { ...typography.caption, color: t.colors.textMuted },
    }),
  );

  return (
    <View style={styles.root}>
      <Text style={styles.title}>{title}</Text>
      {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
    </View>
  );
}
