import { useEffect } from 'react';
import { StyleSheet, View } from 'react-native';
import Animated, {
  Easing,
  useAnimatedStyle,
  useSharedValue,
  withDelay,
  withRepeat,
  withSequence,
  withTiming,
} from 'react-native-reanimated';
import { Text } from '../../../components/Text';
import { fonts } from '../../../theme/fonts';
import { useThemedStyles } from '../../../theme/useAppTheme';

function TypingDot({ delay }: { delay: number }) {
  const opacity = useSharedValue(0.35);

  useEffect(() => {
    opacity.value = withDelay(
      delay,
      withRepeat(
        withSequence(
          withTiming(1, { duration: 360, easing: Easing.inOut(Easing.ease) }),
          withTiming(0.35, { duration: 360, easing: Easing.inOut(Easing.ease) }),
        ),
        -1,
        false,
      ),
    );
  }, [delay, opacity]);

  const style = useAnimatedStyle(() => ({ opacity: opacity.value }));

  return <Animated.View style={[styles.dot, style]} />;
}

export function ChatTypingIndicator({ users }: { users: string[] }) {
  const shellStyles = useShellStyles();
  const label = users.length > 1 ? `${users[0]} та інші пишуть` : `${users[0]} пише`;

  return (
    <View style={shellStyles.wrap}>
      <View style={shellStyles.bubble}>
        <View style={shellStyles.dots}>
          <TypingDot delay={0} />
          <TypingDot delay={120} />
          <TypingDot delay={240} />
        </View>
        <Text numberOfLines={1} style={shellStyles.caption}>
          {label}
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: 'rgba(235,235,245,0.72)',
  },
});

function useShellStyles() {
  return useThemedStyles((t) => {
    const isDark = t.scheme === 'dark';
    return StyleSheet.create({
      wrap: {
        paddingHorizontal: 14,
        paddingBottom: 6,
      },
      bubble: {
        alignSelf: 'flex-start',
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        paddingHorizontal: 12,
        paddingVertical: 8,
        borderRadius: 18,
        backgroundColor: isDark ? '#2C2C2E' : '#E9E9EB',
      },
      dots: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
      },
      caption: {
        fontSize: 11,
        fontFamily: fonts.regular,
        color: isDark ? 'rgba(235,235,245,0.55)' : t.colors.textMuted,
        maxWidth: 180,
      },
    });
  });
}
