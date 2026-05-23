import type { TextProps } from 'react-native';
import { Text as RNText, StyleSheet } from 'react-native';
import { productType } from '../../design/system';
import { useThemedStyles } from '../../theme/useAppTheme';
import { fonts } from '../../theme/fonts';

export type AppTextVariant =
  | 'display'
  | 'screenTitle'
  | 'sectionTitle'
  | 'cardTitle'
  | 'body'
  | 'meta'
  | 'badge';

type Props = TextProps & {
  variant?: AppTextVariant;
  muted?: boolean;
  accent?: boolean;
};

const weightMap = {
  '400': fonts.regular,
  '500': fonts.medium,
  '600': fonts.semiBold,
  '700': fonts.bold,
} as const;

export function AppText({ variant = 'body', muted, accent, style, ...props }: Props) {
  const spec = productType[variant];
  const styles = useThemedStyles((t) =>
    StyleSheet.create({
      text: {
        fontFamily: weightMap[spec.weight],
        fontSize: spec.size,
        lineHeight: spec.line,
        color: accent ? t.colors.primary : muted ? t.colors.textSecondary : t.colors.textPrimary,
      },
    }),
  );

  return <RNText {...props} style={[styles.text, style]} />;
}
