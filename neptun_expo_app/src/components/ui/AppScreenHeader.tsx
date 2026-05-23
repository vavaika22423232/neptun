import { Ionicons } from '@expo/vector-icons';
import type { ComponentProps, ReactNode } from 'react';
import { memo } from 'react';
import { StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Text } from '../Text';
import { NeptunPressable } from '../../design/components/NeptunPressable';
import { useAppTheme, useThemedStyles } from '../../theme/useAppTheme';
import { fonts } from '../../theme/fonts';
import { HeaderLiveIndicator } from './HeaderLiveIndicator';

export type AppScreenHeaderProps = {
  title: string;
  titleIcon?: ComponentProps<typeof Ionicons>['name'];
  subtitle?: string;
  liveCount?: number;
  isLive?: boolean;
  actions?: ReactNode;
  showTelegramFooter?: boolean;
  onBrandPress?: () => void;
  onTelegramPress?: () => void;
};

function AppScreenHeaderInner({
  title,
  titleIcon,
  subtitle,
  liveCount = 0,
  isLive = false,
  actions,
  showTelegramFooter = true,
  onBrandPress,
  onTelegramPress,
}: AppScreenHeaderProps) {
  const insets = useSafeAreaInsets();
  const { theme } = useAppTheme();
  const styles = useAppScreenHeaderStyles();
  const showLive = isLive && liveCount > 0;

  return (
    <View style={[styles.shell, { paddingTop: insets.top + 10, backgroundColor: theme.colors.background }]}>
      <View
        style={[
          styles.panel,
          {
            backgroundColor: theme.colors.surfaceGlassStrong,
            borderColor: theme.colors.border,
            shadowColor: theme.scheme === 'light' ? 'rgba(15, 23, 42, 0.08)' : 'rgba(0, 0, 0, 0.35)',
          },
        ]}
      >
        <View style={styles.mainRow}>
          <NeptunPressable haptic={false} scaleTo={0.99} style={styles.brand} onPress={onBrandPress}>
            <Text style={styles.title}>{title}</Text>
            <View style={styles.statusRow}>
              {titleIcon ? (
                <Ionicons name={titleIcon} size={15} color={theme.colors.textSecondary} />
              ) : null}
              {subtitle ? (
                <Text style={styles.subtitle} numberOfLines={2}>
                  {subtitle}
                </Text>
              ) : null}
              {showLive ? (
                <>
                  <HeaderLiveIndicator active />
                  <Text style={styles.liveCount}>{liveCount}</Text>
                </>
              ) : null}
            </View>
          </NeptunPressable>
          {actions ? <View style={styles.actions}>{actions}</View> : null}
        </View>

        {showTelegramFooter && onTelegramPress ? (
          <>
            <View style={[styles.divider, { backgroundColor: theme.colors.divider }]} />
            <NeptunPressable haptic scaleTo={0.99} style={styles.telegramRow} onPress={onTelegramPress}>
              <View style={[styles.telegramIconWrap, { backgroundColor: theme.colors.surfaceHighlight }]}>
                <Ionicons name="paper-plane" size={17} color={theme.colors.primary} />
              </View>
              <Text style={styles.telegramLabel} numberOfLines={1}>
                Офіційний Telegram канал
              </Text>
              <Ionicons name="chevron-forward" size={18} color={theme.colors.textSecondary} />
            </NeptunPressable>
          </>
        ) : null}
      </View>
    </View>
  );
}

function useAppScreenHeaderStyles() {
  return useThemedStyles((t) =>
    StyleSheet.create({
      shell: { width: '100%' },
      panel: {
        paddingHorizontal: 20,
        paddingBottom: 14,
        borderBottomLeftRadius: 28,
        borderBottomRightRadius: 28,
        borderWidth: StyleSheet.hairlineWidth,
        shadowOffset: { width: 0, height: 8 },
        shadowOpacity: 1,
        shadowRadius: 20,
        elevation: 6,
      },
      mainRow: {
        flexDirection: 'row',
        alignItems: 'flex-start',
        gap: 10,
        paddingBottom: 10,
      },
      brand: { flex: 1, minWidth: 0, gap: 5 },
      title: {
        fontFamily: fonts.bold,
        fontSize: 28,
        letterSpacing: -0.5,
        lineHeight: 32,
        color: t.colors.textPrimary,
      },
      statusRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        flexWrap: 'wrap',
      },
      subtitle: {
        fontFamily: fonts.medium,
        fontSize: 14,
        color: t.colors.textSecondary,
        flexShrink: 1,
      },
      liveCount: {
        fontFamily: fonts.semiBold,
        fontSize: 14,
        color: t.colors.live,
        minWidth: 24,
      },
      actions: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        paddingTop: 2,
        flexShrink: 0,
      },
      divider: {
        height: StyleSheet.hairlineWidth,
        marginBottom: 10,
      },
      telegramRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
        minHeight: 42,
      },
      telegramIconWrap: {
        width: 36,
        height: 36,
        borderRadius: 18,
        alignItems: 'center',
        justifyContent: 'center',
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: t.colors.border,
      },
      telegramLabel: {
        flex: 1,
        fontFamily: fonts.semiBold,
        fontSize: 15,
        color: t.colors.textPrimary,
      },
    }),
  );
}

export const AppScreenHeader = memo(AppScreenHeaderInner);
