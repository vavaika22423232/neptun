import { useEffect } from 'react';
import { StyleSheet, View } from 'react-native';
import Animated, {
  Easing,
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withTiming,
} from 'react-native-reanimated';
import { useThemedStyles } from '../../../theme/useAppTheme';
import { RadarFeedCard } from './RadarFeedCard';

function ShimmerRow({ blockStyle }: { blockStyle: object }) {
  const opacity = useSharedValue(0.35);

  useEffect(() => {
    opacity.value = withRepeat(
      withTiming(0.85, { duration: 900, easing: Easing.inOut(Easing.ease) }),
      -1,
      true,
    );
  }, [opacity]);

  const animStyle = useAnimatedStyle(() => ({ opacity: opacity.value }));

  return (
    <View style={stylesRow.row}>
      <Animated.View style={[blockStyle, animStyle, stylesRow.icon]} />
      <View style={stylesRow.lines}>
        <Animated.View style={[blockStyle, animStyle, stylesRow.lineLg]} />
        <Animated.View style={[blockStyle, animStyle, stylesRow.lineSm]} />
      </View>
    </View>
  );
}

const stylesRow = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: 12, padding: 14 },
  icon: { width: 40, height: 40, borderRadius: 12 },
  lines: { flex: 1, gap: 8 },
  lineLg: { height: 14, borderRadius: 7, width: '72%' },
  lineSm: { height: 10, borderRadius: 5, width: '48%' },
});

export function RadarShimmerList({ count = 6 }: { count?: number }) {
  const styles = useThemedStyles((t) =>
    StyleSheet.create({
      wrap: { paddingHorizontal: t.radar.padH, paddingTop: 8, gap: t.radar.cardGap },
      block: {
        backgroundColor: t.scheme === 'light' ? '#ECECF0' : 'rgba(255,255,255,0.08)',
      },
    }),
  );

  return (
    <View style={styles.wrap}>
      <RadarFeedCard>
        {Array.from({ length: count }, (_, i) => (
          <ShimmerRow key={i} blockStyle={styles.block} />
        ))}
      </RadarFeedCard>
    </View>
  );
}
