import type { TextProps } from 'react-native';
import { Text as RNText, StyleSheet } from 'react-native';
import { useThemedStyles } from '../theme/useAppTheme';
import { fonts } from '../theme/fonts';

type Props = TextProps & {
  muted?: boolean;
  title?: boolean;
  subtitle?: boolean;
  caption?: boolean;
};

export function Text({ style, muted, title, subtitle, caption, ...props }: Props) {
  const styles = useThemedStyles((theme) =>
    StyleSheet.create({
      base: {
        color: theme.colors.textPrimary,
        fontFamily: fonts.regular,
        ...theme.typography.body,
      },
      muted: { color: theme.colors.textMuted },
      title: {
        fontFamily: fonts.bold,
        ...theme.typography.title1,
        marginBottom: 8,
      },
      subtitle: {
        fontFamily: fonts.semiBold,
        ...theme.typography.title3,
      },
      caption: {
        fontFamily: fonts.medium,
        ...theme.typography.caption,
        color: theme.colors.textMuted,
      },
    }),
  );

  return (
    <RNText
      {...props}
      style={[
        styles.base,
        muted && styles.muted,
        title && styles.title,
        subtitle && styles.subtitle,
        caption && styles.caption,
        style,
      ]}
    />
  );
}
