import type { PressableProps, StyleProp, ViewStyle } from 'react-native';
import { voidHapticImpact } from '../../utils/lazyExpoNative';
import { Pressable } from 'react-native';
import Animated, { useAnimatedStyle, useSharedValue, withTiming } from 'react-native-reanimated';

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

type Props = PressableProps & {
  haptic?: boolean;
  scaleTo?: number;
  containerStyle?: StyleProp<ViewStyle>;
};

export function NeptunPressable({
  haptic = true,
  scaleTo = 0.98,
  containerStyle,
  onPressIn,
  onPressOut,
  onPress,
  style,
  children,
  ...rest
}: Props) {
  const scale = useSharedValue(1);
  const animStyle = useAnimatedStyle(() => ({ transform: [{ scale: scale.value }] }));

  return (
    <AnimatedPressable
      {...rest}
      style={[containerStyle, animStyle, style as StyleProp<ViewStyle>]}
      onPressIn={(e) => {
        scale.value = withTiming(scaleTo, { duration: 100 });
        onPressIn?.(e);
      }}
      onPressOut={(e) => {
        scale.value = withTiming(1, { duration: 160 });
        onPressOut?.(e);
      }}
      onPress={(e) => {
        if (haptic) voidHapticImpact('light');
        onPress?.(e);
      }}
    >
      {children}
    </AnimatedPressable>
  );
}
