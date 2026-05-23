import { useEffect } from 'react';
import { StyleSheet, View } from 'react-native';
import Animated, {
  Easing,
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withSequence,
  withTiming,
} from 'react-native-reanimated';
import { Text } from '../../components/Text';
import { fonts } from '../../theme/fonts';
import { useThemedStyles } from '../../theme/useAppTheme';
import { typography } from '../tokens';

/** Premium boot canvas while fonts / version gate load. */
export function NeptunBootSplash() {
  const styles = useThemedStyles((t) =>
    StyleSheet.create({
      root: {
        flex: 1,
        backgroundColor: t.colors.background,
        alignItems: 'center',
        justifyContent: 'center',
        gap: 10,
      },
      logoRing: {
        width: 88,
        height: 88,
        borderRadius: t.radii.pill,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: t.colors.primaryMuted,
        marginBottom: 8,
      },
      logoCore: {
        width: 64,
        height: 64,
        borderRadius: 20,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: t.colors.surfaceElevated,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: t.colors.borderStrong,
        ...t.shadows.sm,
      },
      logoLetter: {
        fontFamily: fonts.bold,
        fontSize: 28,
        color: t.colors.primary,
        letterSpacing: -0.5,
      },
      title: {
        fontFamily: fonts.bold,
        ...typography.title1,
        letterSpacing: -0.3,
        color: t.colors.textPrimary,
      },
      subtitle: {
        ...typography.caption,
        letterSpacing: 1.2,
        textTransform: 'uppercase',
        color: t.colors.textMuted,
      },
    }),
  );

  const pulse = useSharedValue(0.92);
  const glow = useSharedValue(0.35);

  useEffect(() => {
    pulse.value = withRepeat(
      withSequence(
        withTiming(1, { duration: 900, easing: Easing.inOut(Easing.ease) }),
        withTiming(0.92, { duration: 900, easing: Easing.inOut(Easing.ease) }),
      ),
      -1,
      false,
    );
    glow.value = withRepeat(
      withTiming(0.65, { duration: 1200, easing: Easing.inOut(Easing.ease) }),
      -1,
      true,
    );
  }, [pulse, glow]);

  const logoStyle = useAnimatedStyle(() => ({
    transform: [{ scale: pulse.value }],
    opacity: glow.value,
  }));

  return (
    <View style={styles.root}>
      <Animated.View style={[styles.logoRing, logoStyle]}>
        <View style={styles.logoCore}>
          <Text style={styles.logoLetter}>N</Text>
        </View>
      </Animated.View>
      <Text style={styles.title}>Neptun</Text>
      <Text style={styles.subtitle}>Dron Alerts</Text>
    </View>
  );
}
