import type { ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';
import { productSpacing } from '../../design/system';
import { useThemedStyles } from '../../theme/useAppTheme';
import { AppText } from './AppText';

type Props = {
  title?: string;
  subtitle?: string;
  children: ReactNode;
  gap?: number;
};

export function AppSection({ title, subtitle, children, gap = productSpacing.stackGap }: Props) {
  const styles = useThemedStyles((t) =>
    StyleSheet.create({
      root: { gap: productSpacing.sectionGap },
      head: { gap: 4, paddingHorizontal: t.spacing.screenH },
    }),
  );

  return (
    <View style={styles.root}>
      {title ? (
        <View style={styles.head}>
          <AppText variant="sectionTitle">{title}</AppText>
          {subtitle ? <AppText variant="meta" muted>{subtitle}</AppText> : null}
        </View>
      ) : null}
      <View style={{ gap }}>{children}</View>
    </View>
  );
}
