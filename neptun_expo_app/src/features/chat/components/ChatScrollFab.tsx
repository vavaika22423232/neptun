import { Ionicons } from '@expo/vector-icons';
import { useEffect } from 'react';
import { StyleSheet, Text } from 'react-native';
import Animated, {
  Easing,
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withSequence,
  withTiming,
} from 'react-native-reanimated';
import { NeptunPressable } from '../../../design/components/NeptunPressable';
import { fonts } from '../../../theme/fonts';
import { useThemedStyles } from '../../../theme/useAppTheme';

type Props = {
  bottom: number;
  unreadCount: number;
  onPress: () => void;
};

export function ChatScrollFab({ bottom, unreadCount, onPress }: Props) {
  const styles = useFabStyles();
  const scale = useSharedValue(1);

  useEffect(() => {
    if (unreadCount <= 0) {
      scale.value = 1;
      return;
    }
    scale.value = withRepeat(
      withSequence(
        withTiming(1.06, { duration: 600, easing: Easing.inOut(Easing.ease) }),
        withTiming(1, { duration: 600, easing: Easing.inOut(Easing.ease) }),
      ),
      -1,
      false,
    );
  }, [scale, unreadCount]);

  const badgeStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }));

  return (
    <NeptunPressable haptic onPress={onPress} style={[styles.fab, { bottom }]}>
      <Ionicons name="chevron-down" size={20} color={styles.iconColor.color} />
      {unreadCount > 0 ? (
        <Animated.View style={[styles.badge, badgeStyle]}>
          <Text style={styles.badgeText}>{unreadCount > 99 ? '99+' : unreadCount}</Text>
        </Animated.View>
      ) : null}
    </NeptunPressable>
  );
}

function useFabStyles() {
  return useThemedStyles((t) => {
    const isDark = t.scheme === 'dark';
    return StyleSheet.create({
      fab: {
        position: 'absolute',
        right: 14,
        width: 44,
        height: 44,
        borderRadius: 22,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: isDark ? '#2C2C2E' : '#FFFFFF',
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: isDark ? 'rgba(255,255,255,0.08)' : t.colors.border,
        shadowColor: '#000',
        shadowOpacity: isDark ? 0.35 : 0.12,
        shadowRadius: 10,
        shadowOffset: { width: 0, height: 3 },
        elevation: 6,
      },
      iconColor: { color: t.colors.textPrimary },
      badge: {
        position: 'absolute',
        top: -4,
        right: -4,
        minWidth: 20,
        height: 20,
        borderRadius: 10,
        paddingHorizontal: 5,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: t.colors.primary,
      },
      badgeText: {
        color: '#FFFFFF',
        fontFamily: fonts.bold,
        fontSize: 10,
      },
    });
  });
}
