import { StyleSheet, View } from 'react-native';

type Props = {
  total: number;
  current: number;
};

/** Minimal onboarding pager — elongated active dot. */
export function PageDots({ total, current }: Props) {
  return (
    <View style={styles.row}>
      {Array.from({ length: total }, (_, i) => (
        <View key={i} style={[styles.dot, i === current && styles.dotActive]} />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  dot: {
    width: 7,
    height: 7,
    borderRadius: 4,
    backgroundColor: 'rgba(60,60,67,0.18)',
  },
  dotActive: {
    width: 22,
    backgroundColor: '#000000',
  },
});
