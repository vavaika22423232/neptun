import { ActivityIndicator, StyleSheet, View } from 'react-native';
import { Text } from '../../components/Text';
import { palette, spacing } from '../tokens';

type Props = {
  label?: string;
  size?: 'small' | 'large';
};

export function NeptunLoading({ label, size = 'large' }: Props) {
  return (
    <View style={styles.root}>
      <ActivityIndicator size={size} color={palette.accent} />
      {label ? <Text muted style={styles.label}>{label}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: spacing.xxxl,
    gap: spacing.md,
  },
  label: { fontSize: 13 },
});
