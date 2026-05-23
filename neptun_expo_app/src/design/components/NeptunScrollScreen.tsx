import type { ScrollViewProps } from 'react-native';
import { ScrollView, StyleSheet, View, type ViewProps } from 'react-native';
import { palette, spacing } from '../tokens';

type ScrollProps = ScrollViewProps & { padded?: boolean };
type ViewScreenProps = ViewProps & { padded?: boolean };

export function NeptunScrollScreen({ style, contentContainerStyle, padded = true, children, ...props }: ScrollProps) {
  return (
    <ScrollView
      {...props}
      style={[styles.root, style]}
      contentContainerStyle={[padded && styles.pad, contentContainerStyle]}
    >
      {children}
    </ScrollView>
  );
}

export function NeptunViewScreen({ style, padded = true, children, ...props }: ViewScreenProps) {
  return (
    <View {...props} style={[styles.root, padded && styles.pad, style]}>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: palette.bg },
  pad: { padding: spacing.screenH, paddingBottom: spacing.xxxl, gap: spacing.md },
});
