import { Ionicons } from '@expo/vector-icons';
import { memo } from 'react';
import { StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Text } from '../../../components/Text';
import { HeaderLiveIndicator } from '../../../components/ui/HeaderLiveIndicator';
import { NeptunPressable } from '../../../design/components/NeptunPressable';
import { fonts } from '../../../theme/fonts';
import { useThemedStyles } from '../../../theme/useAppTheme';

export type RadarTabHeaderProps = {
  isLive: boolean;
  statusLine: string;
  showModeratorAction?: boolean;
  onBrandPress?: () => void;
  onSearchPress?: () => void;
  onTelegramPress?: () => void;
  onModeratorPress?: () => void;
};

/** Minimal iOS header — title, live strip, circle actions (no heavy top bar). */
function RadarTabHeaderInner({
  isLive,
  statusLine,
  showModeratorAction,
  onBrandPress,
  onSearchPress,
  onTelegramPress,
  onModeratorPress,
}: RadarTabHeaderProps) {
  const insets = useSafeAreaInsets();
  const styles = useHeaderStyles();

  return (
    <View style={[styles.shell, { paddingTop: insets.top }]}>
      <View style={styles.bar}>
        {showModeratorAction ? (
          <NeptunPressable
            haptic
            style={styles.iconBtn}
            accessibilityLabel="Модератор"
            onPress={onModeratorPress}
          >
            <Ionicons name="shield-checkmark" size={20} color={styles.iconColor.color} />
          </NeptunPressable>
        ) : (
          <View style={styles.sideSpacer} />
        )}

        <NeptunPressable
          haptic={false}
          style={styles.center}
          accessibilityLabel="Радар NEPTUN"
          onLongPress={onBrandPress}
          onPress={onBrandPress}
        >
          <Text style={styles.title} numberOfLines={1}>
            Радар
          </Text>
          <View style={styles.statusRow}>
            <HeaderLiveIndicator active={isLive} size="sm" />
            <Text style={styles.status} numberOfLines={1}>
              {statusLine}
            </Text>
          </View>
        </NeptunPressable>

        <View style={styles.actions}>
          {onSearchPress ? (
            <NeptunPressable
              haptic
              style={styles.iconBtn}
              accessibilityLabel="Пошук"
              onPress={onSearchPress}
            >
              <Ionicons name="search-outline" size={20} color={styles.iconColor.color} />
            </NeptunPressable>
          ) : null}
          {onTelegramPress ? (
            <NeptunPressable
              haptic
              style={styles.iconBtn}
              accessibilityLabel="Telegram"
              onPress={onTelegramPress}
            >
              <Ionicons name="paper-plane-outline" size={20} color={styles.iconColor.color} />
            </NeptunPressable>
          ) : null}
        </View>
      </View>
    </View>
  );
}

function useHeaderStyles() {
  return useThemedStyles((t) => {
    const isDark = t.scheme === 'dark';
    return StyleSheet.create({
      shell: {
        backgroundColor: isDark ? t.colors.background : t.colors.cardMuted,
      },
      bar: {
        minHeight: 52,
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: 10,
        paddingBottom: 10,
        gap: 4,
      },
      sideSpacer: { width: 40 },
      iconBtn: {
        width: 40,
        height: 40,
        borderRadius: 20,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)',
      },
      iconColor: { color: t.colors.textPrimary },
      center: {
        flex: 1,
        alignItems: 'center',
        gap: 3,
        paddingHorizontal: 4,
      },
      title: {
        fontFamily: fonts.semiBold,
        fontSize: 17,
        letterSpacing: -0.2,
        color: t.colors.textPrimary,
      },
      statusRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
        maxWidth: '100%',
      },
      status: {
        fontFamily: fonts.regular,
        fontSize: 12,
        color: t.colors.textMuted,
        flexShrink: 1,
      },
      actions: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
        minWidth: 40,
        justifyContent: 'flex-end',
      },
    });
  });
}

export const RadarTabHeader = memo(RadarTabHeaderInner);
