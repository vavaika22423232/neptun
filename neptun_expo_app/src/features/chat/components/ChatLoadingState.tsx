import { ActivityIndicator, StyleSheet, View } from 'react-native';
import Animated, {
  Easing,
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withTiming,
} from 'react-native-reanimated';
import { useEffect } from 'react';
import { Text } from '../../../components/Text';
import { useThemedStyles } from '../../../theme/useAppTheme';

export function ChatLoadingState() {
  const pulse = useSharedValue(0.45);
  const styles = useLoadingStyles();

  useEffect(() => {
    pulse.value = withRepeat(
      withTiming(1, { duration: 900, easing: Easing.inOut(Easing.ease) }),
      -1,
      true,
    );
  }, [pulse]);

  const shimmerStyle = useAnimatedStyle(() => ({ opacity: pulse.value }));

  return (
    <View style={styles.root}>
      <Animated.View style={[styles.bubbleLeft, shimmerStyle]} />
      <Animated.View style={[styles.bubbleRight, shimmerStyle]} />
      <Animated.View style={[styles.bubbleLeftSm, shimmerStyle]} />
      <ActivityIndicator color={styles.spinnerColor.color} style={{ marginTop: 32 }} />
      <Text muted style={{ marginTop: 12 }}>
        Завантаження чату…
      </Text>
    </View>
  );
}

function useLoadingStyles() {
  return useThemedStyles((t) => {
    const isDark = t.scheme === 'dark';
    return StyleSheet.create({
      root: {
        flex: 1,
        backgroundColor: t.chat.bg,
        padding: 24,
        justifyContent: 'center',
      },
      bubbleLeft: {
        width: '68%',
        height: 52,
        borderRadius: 20,
        backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
        marginBottom: 12,
      },
      bubbleRight: {
        alignSelf: 'flex-end',
        width: '58%',
        height: 44,
        borderRadius: 20,
        backgroundColor: isDark ? 'rgba(255,255,255,0.14)' : '#FFFFFF',
        marginBottom: 12,
      },
      bubbleLeftSm: {
        width: '52%',
        height: 40,
        borderRadius: 18,
        backgroundColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)',
      },
      spinnerColor: { color: t.colors.textMuted },
    });
  });
}
