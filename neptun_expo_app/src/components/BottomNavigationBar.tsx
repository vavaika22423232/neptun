import { Ionicons } from '@expo/vector-icons';
import type { BottomTabBarProps } from '@react-navigation/bottom-tabs';
import { useCallback, useEffect, useRef } from 'react';
import { StyleSheet, View, type View as RNView } from 'react-native';
import Animated, {
  FadeIn,
  FadeOut,
  useAnimatedStyle,
  useSharedValue,
  withSpring,
} from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { NeptunPressable } from '../design/components/NeptunPressable';
import { useAppTheme, useThemedStyles } from '../theme/useAppTheme';
import { fonts } from '../theme/fonts';
import { Text } from './Text';

const HIDDEN_TABS = new Set(['regions']);

const SPRING = { damping: 19, stiffness: 240, mass: 0.85 };

const icons: Record<string, React.ComponentProps<typeof Ionicons>['name']> = {
  index: 'map-outline',
  radar: 'radio-outline',
  regions: 'notifications-outline',
  chat: 'chatbubble-outline',
  profile: 'person-outline',
};

const selectedIcons: Record<string, React.ComponentProps<typeof Ionicons>['name']> = {
  index: 'map',
  radar: 'radio',
  regions: 'notifications',
  chat: 'chatbubble',
  profile: 'person',
};

type TabLayout = { x: number; width: number; height: number };

const BAR_TOP_PAD = 8;
const BAR_HEIGHT = 58;

/** Total vertical space occupied by the floating tab bar (incl. safe area). */
export function bottomNavOccupiedHeight(safeBottom: number): number {
  return BAR_TOP_PAD + BAR_HEIGHT + Math.max(safeBottom, 10);
}

/** @deprecated use bottomNavOccupiedHeight(safeBottom) */
export const BOTTOM_NAV_CLEARANCE = bottomNavOccupiedHeight(34);

/** Composer gap above the tab bar (scene already ends at the tab bar slot). */
export function bottomNavComposerInset(_safeBottom: number): number {
  return 12;
}

function TabItem({
  focused,
  label,
  routeName,
  onPress,
  barRef,
  onLayout,
}: {
  focused: boolean;
  label: string;
  routeName: string;
  onPress: () => void;
  barRef: React.RefObject<RNView | null>;
  onLayout: (layout: TabLayout) => void;
}) {
  const { theme } = useAppTheme();
  const styles = useTabStyles();
  const isDark = theme.scheme === 'dark';
  const itemRef = useRef<RNView>(null);

  const inactiveColor = isDark ? theme.colors.tabInactiveText : theme.colors.textPrimary;
  const activeColor = isDark ? '#000000' : '#FFFFFF';

  const iconScale = useSharedValue(focused ? 1.06 : 1);
  useEffect(() => {
    iconScale.value = withSpring(focused ? 1.06 : 1, SPRING);
  }, [focused, iconScale]);

  const iconAnim = useAnimatedStyle(() => ({
    transform: [{ scale: iconScale.value }],
  }));

  const reportLayout = useCallback(() => {
    const bar = barRef.current;
    const item = itemRef.current;
    if (!bar || !item) return;
    item.measureLayout(
      bar,
      (x, _y, width, height) => onLayout({ x, width, height }),
      () => {},
    );
  }, [barRef, onLayout]);

  useEffect(() => {
    if (focused) {
      const t = setTimeout(reportLayout, 0);
      return () => clearTimeout(t);
    }
    reportLayout();
    return undefined;
  }, [focused, label, reportLayout]);

  return (
    <NeptunPressable
      haptic
      accessibilityRole="button"
      accessibilityState={focused ? { selected: true } : {}}
      accessibilityLabel={label}
      onPress={onPress}
      style={styles.item}
    >
      <View
        ref={itemRef}
        onLayout={reportLayout}
        style={[styles.itemInner, focused && styles.itemInnerActive]}
      >
        <Animated.View style={[iconAnim, !focused && styles.iconShadow]}>
          <Ionicons
            name={(focused ? selectedIcons[routeName] : icons[routeName]) ?? 'ellipse-outline'}
            size={20}
            color={focused ? activeColor : inactiveColor}
          />
        </Animated.View>
        {focused ? (
          <Animated.View entering={FadeIn.duration(180)} exiting={FadeOut.duration(120)}>
            <Text style={[styles.labelActive, { color: activeColor }]} numberOfLines={1}>
              {label}
            </Text>
          </Animated.View>
        ) : null}
      </View>
    </NeptunPressable>
  );
}

/** Floating tab bar — transparent shell, sliding active capsule only. */
export function BottomNavigationBar({ state, descriptors, navigation }: BottomTabBarProps) {
  const insets = useSafeAreaInsets();
  const styles = useShellStyles();
  const { theme } = useAppTheme();
  const isDark = theme.scheme === 'dark';
  const barRef = useRef<RNView>(null);

  const visibleRoutes = state.routes.filter((r) => !HIDDEN_TABS.has(r.name));
  const activeVisibleIndex = visibleRoutes.findIndex(
    (r) => state.routes.indexOf(r) === state.index,
  );

  const tabLayouts = useRef<(TabLayout | null)[]>(visibleRoutes.map(() => null));
  const pillX = useSharedValue(0);
  const pillWidth = useSharedValue(44);
  const pillHeight = useSharedValue(44);
  const pillReady = useSharedValue(0);

  const movePill = useCallback(
    (index: number) => {
      const layout = tabLayouts.current[index];
      if (!layout) return;
      pillX.value = withSpring(layout.x, SPRING);
      pillWidth.value = withSpring(layout.width, SPRING);
      pillHeight.value = withSpring(layout.height, SPRING);
      pillReady.value = withSpring(1, SPRING);
    },
    [pillHeight, pillReady, pillWidth, pillX],
  );

  useEffect(() => {
    if (activeVisibleIndex >= 0) {
      movePill(activeVisibleIndex);
    }
  }, [activeVisibleIndex, movePill, state.index]);

  const pillStyle = useAnimatedStyle(() => ({
    opacity: pillReady.value,
    transform: [{ translateX: pillX.value }],
    width: pillWidth.value,
    height: pillHeight.value,
  }));

  const pillColor = isDark ? '#FFFFFF' : theme.colors.textPrimary;

  return (
    <View
      pointerEvents="box-none"
      style={[styles.outer, { paddingBottom: Math.max(insets.bottom, 10) }]}
    >
      <View ref={barRef} style={styles.bar} pointerEvents="box-none">
        <Animated.View
          pointerEvents="none"
          style={[styles.pill, { backgroundColor: pillColor }, pillStyle]}
        />
        {visibleRoutes.map((route, visibleIndex) => {
          const routeIndex = state.routes.indexOf(route);
          const focused = state.index === routeIndex;
          const label =
            descriptors[route.key].options.tabBarLabel?.toString() ??
            descriptors[route.key].options.title ??
            route.name;
          return (
            <TabItem
              key={route.key}
              focused={focused}
              label={label}
              routeName={route.name}
              barRef={barRef}
              onLayout={(layout) => {
                tabLayouts.current[visibleIndex] = layout;
                if (focused) movePill(visibleIndex);
              }}
              onPress={() => {
                const event = navigation.emit({
                  type: 'tabPress',
                  target: route.key,
                  canPreventDefault: true,
                });
                if (!focused && !event.defaultPrevented) navigation.navigate(route.name);
              }}
            />
          );
        })}
      </View>
    </View>
  );
}

function useShellStyles() {
  return useThemedStyles((t) => {
    const isLight = t.scheme === 'light';
    return StyleSheet.create({
      outer: {
        paddingHorizontal: 16,
        paddingTop: BAR_TOP_PAD,
        backgroundColor: 'transparent',
      },
      bar: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        minHeight: BAR_HEIGHT,
        padding: 6,
      },
      pill: {
        position: 'absolute',
        left: 0,
        top: 6,
        borderRadius: 24,
        shadowColor: '#000000',
        shadowOpacity: isLight ? 0.12 : 0.22,
        shadowRadius: isLight ? 8 : 10,
        shadowOffset: { width: 0, height: isLight ? 2 : 4 },
        elevation: isLight ? 3 : 6,
      },
    });
  });
}

function useTabStyles() {
  return useThemedStyles((t) => {
    const isLight = t.scheme === 'light';
    return StyleSheet.create({
      item: {
        flex: 1,
        zIndex: 1,
      },
      itemInner: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: 44,
        paddingHorizontal: 8,
        gap: 6,
      },
      itemInnerActive: {
        paddingHorizontal: 14,
      },
      labelActive: {
        fontFamily: fonts.semiBold,
        fontSize: 14,
        lineHeight: 18,
      },
      iconShadow: isLight
        ? {}
        : {
            shadowColor: '#000000',
            shadowOpacity: 0.28,
            shadowRadius: 3,
            shadowOffset: { width: 0, height: 1 },
          },
    });
  });
}

/** @deprecated use BottomNavigationBar */
export const NeptunTabBar = BottomNavigationBar;
