import type { ReactNode } from 'react';
import { useCallback, useRef } from 'react';
import { FlatList, StyleSheet, useWindowDimensions, View } from 'react-native';
import Animated, {
  Extrapolation,
  interpolate,
  useAnimatedScrollHandler,
  useAnimatedStyle,
  type SharedValue,
} from 'react-native-reanimated';

const AnimatedFlatList = Animated.createAnimatedComponent(FlatList<number>);

type Props = {
  page: number;
  onPageChange: (index: number) => void;
  scrollEnabled?: boolean;
  renderPage: (index: number) => ReactNode;
  totalPages: number;
  pagerRef?: React.RefObject<FlatList<number> | null>;
  scrollX: SharedValue<number>;
  pageWidth?: number;
};

function OnboardingPageFrame({
  index,
  width,
  scrollX,
  children,
}: {
  index: number;
  width: number;
  scrollX: SharedValue<number>;
  children: ReactNode;
}) {
  const style = useAnimatedStyle(() => {
    const center = index * width;
    const opacity = interpolate(
      scrollX.value,
      [center - width, center, center + width],
      [0.45, 1, 0.45],
      Extrapolation.CLAMP,
    );
    const scale = interpolate(
      scrollX.value,
      [center - width, center, center + width],
      [0.96, 1, 0.96],
      Extrapolation.CLAMP,
    );
    const translateY = interpolate(
      scrollX.value,
      [center - width, center, center + width],
      [14, 0, 14],
      Extrapolation.CLAMP,
    );
    return {
      opacity,
      transform: [{ scale }, { translateY }],
    };
  });

  return (
    <Animated.View style={[{ width, flex: 1 }, style]}>
      {children}
    </Animated.View>
  );
}

/** Horizontal pager with parallax fade/scale while swiping. */
export function OnboardingPager({
  page,
  onPageChange,
  scrollEnabled = true,
  renderPage,
  totalPages,
  pagerRef: externalRef,
  scrollX,
  pageWidth: pageWidthProp,
}: Props) {
  const { width: windowWidth } = useWindowDimensions();
  const width = pageWidthProp ?? windowWidth;
  const internalRef = useRef<FlatList<number>>(null);
  const pagerRef = externalRef ?? internalRef;
  const pages = useRef(Array.from({ length: totalPages }, (_, i) => i)).current;

  const onScroll = useAnimatedScrollHandler({
    onScroll: (event) => {
      scrollX.value = event.contentOffset.x;
    },
  });

  const onMomentumEnd = useCallback(
    (offsetX: number) => {
      const next = Math.round(offsetX / width);
      const clamped = Math.min(totalPages - 1, Math.max(0, next));
      if (clamped !== page) onPageChange(clamped);
    },
    [onPageChange, page, totalPages, width],
  );

  return (
    <View style={styles.root}>
      <AnimatedFlatList
        ref={pagerRef}
        data={pages}
        horizontal
        pagingEnabled
        scrollEnabled={scrollEnabled}
        bounces={false}
        decelerationRate="fast"
        showsHorizontalScrollIndicator={false}
        keyExtractor={(item) => String(item)}
        onScroll={onScroll}
        scrollEventThrottle={16}
        onMomentumScrollEnd={(e) => onMomentumEnd(e.nativeEvent.contentOffset.x)}
        getItemLayout={(_, index) => ({ length: width, offset: width * index, index })}
        renderItem={({ item, index }) => (
          <OnboardingPageFrame index={index} width={width} scrollX={scrollX}>
            {renderPage(item)}
          </OnboardingPageFrame>
        )}
      />
    </View>
  );
}

export function scrollOnboardingToPage(
  ref: React.RefObject<FlatList<number> | null>,
  index: number,
  width: number,
) {
  ref.current?.scrollToOffset({ offset: index * width, animated: true });
}

const styles = StyleSheet.create({
  root: { flex: 1 },
});
