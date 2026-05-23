import { StyleSheet, View } from 'react-native';
import Animated, {
  Extrapolation,
  interpolate,
  useAnimatedStyle,
  type SharedValue,
} from 'react-native-reanimated';

type Props = {
  total: number;
  scrollX: SharedValue<number>;
  pageWidth: number;
};

/** Dots that follow horizontal scroll progress. */
export function AnimatedPageDots({ total, scrollX, pageWidth }: Props) {
  return (
    <View style={styles.row}>
      {Array.from({ length: total }, (_, i) => (
        <AnimatedDot key={i} index={i} scrollX={scrollX} pageWidth={pageWidth} />
      ))}
    </View>
  );
}

function AnimatedDot({
  index,
  scrollX,
  pageWidth,
}: {
  index: number;
  scrollX: SharedValue<number>;
  pageWidth: number;
}) {
  const style = useAnimatedStyle(() => {
    const progress = scrollX.value / pageWidth;
    const distance = Math.abs(progress - index);
    const width = interpolate(distance, [0, 1], [22, 7], Extrapolation.CLAMP);
    const opacity = interpolate(distance, [0, 1], [1, 0.35], Extrapolation.CLAMP);
    return {
      width,
      opacity,
      backgroundColor: distance < 0.5 ? '#000000' : 'rgba(60,60,67,0.18)',
    };
  });

  return <Animated.View style={[styles.dot, style]} />;
}

const styles = StyleSheet.create({
  row: { flex: 1, flexDirection: 'row', alignItems: 'center', gap: 6 },
  dot: {
    height: 7,
    borderRadius: 4,
  },
});
