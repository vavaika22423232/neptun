import type { ViewProps } from 'react-native';
import { StyleSheet, View } from 'react-native';
import { useThemedStyles } from '../../theme/useAppTheme';

type Props = ViewProps & {
  padded?: boolean;
};

export function NeptunScreen({ style, padded, children, ...props }: Props) {
  const styles = useThemedStyles((t) =>
    StyleSheet.create({
      root: {
        flex: 1,
        backgroundColor: t.colors.background,
      },
      padded: {
        paddingHorizontal: t.spacing.screenH,
      },
    }),
  );

  return (
    <View {...props} style={[styles.root, padded && styles.padded, style]}>
      {children}
    </View>
  );
}
