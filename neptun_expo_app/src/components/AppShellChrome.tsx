import { Ionicons } from '@expo/vector-icons';
import { BlurView } from 'expo-blur';
import { LinearGradient } from 'expo-linear-gradient';
import { useRouter } from 'expo-router';
import type { ComponentProps } from 'react';
import { Platform, StyleSheet, View } from 'react-native';
import { openNeptunTelegramChannel } from '../core/utils/openNeptunTelegram';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useModeratorLogoTap } from '../core/moderator/useModeratorLogoTap';
import { chatChromeBridge } from '../features/chat/chatChromeBridge';
import { ModeratorSecretDialog } from '../features/chat/components/ModeratorSecretDialog';
import { useApp } from '../context/AppContext';
import { moderatorService } from '../services/moderatorService';
import { useAppTheme, useThemedStyles } from '../theme/useAppTheme';
import { fonts } from '../theme/fonts';
import { NeptunPressable } from '../design/components/NeptunPressable';
import { OfflineBanner } from './OfflineBanner';
import { Text } from './Text';

type Props = {
  title: string;
  icon: ComponentProps<typeof Ionicons>['name'];
  showChatActions?: boolean;
};

export function AppShellChrome({ title, icon, showChatActions }: Props) {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { onlineCount, isPremium, isModerator, refreshIdentity } = useApp();
  const logoTap = useModeratorLogoTap();
  const { theme } = useAppTheme();
  const p = theme.palette;

  const styles = useThemedStyles((t) => {
    const pal = t.palette;
    return StyleSheet.create({
      root: {
        borderBottomLeftRadius: t.radii.xl,
        borderBottomRightRadius: t.radii.xl,
        borderBottomWidth: StyleSheet.hairlineWidth,
        borderBottomColor: pal.border,
        paddingHorizontal: t.spacing.md,
        overflow: 'hidden',
        ...t.shadows.sm,
      },
      blur: {
        ...StyleSheet.absoluteFillObject,
        backgroundColor: Platform.OS === 'android' ? pal.bgChrome : 'transparent',
      },
      sheen: {
        ...StyleSheet.absoluteFillObject,
        opacity: t.scheme === 'dark' ? 1 : 0.55,
      },
      topRow: {
        minHeight: 64,
        flexDirection: 'row',
        alignItems: 'center',
        gap: t.spacing.xs,
      },
      brand: { flex: 1, minWidth: 0 },
      brandTitle: {
        fontFamily: fonts.bold,
        ...t.typography.title2,
        color: pal.text,
      },
      contextRow: {
        marginTop: 5,
        flexDirection: 'row',
        alignItems: 'center',
        gap: 5,
      },
      contextText: {
        maxWidth: 110,
        color: pal.textMuted,
        fontFamily: fonts.semiBold,
        ...t.typography.micro,
      },
      dotMuted: {
        width: 4,
        height: 4,
        borderRadius: 2,
        backgroundColor: pal.textFaint,
        marginHorizontal: 2,
      },
      onlineDot: {
        width: 6,
        height: 6,
        borderRadius: 3,
        backgroundColor: pal.success,
      },
      onlineText: {
        minWidth: 22,
        color: pal.success,
        fontFamily: fonts.semiBold,
        ...t.typography.micro,
      },
      actionChip: {
        width: 38,
        height: 38,
        borderRadius: t.radii.pill,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: t.colors.surfaceGlass,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: pal.border,
      },
      proChip: {
        height: 38,
        borderRadius: t.radii.pill,
        paddingHorizontal: 12,
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: pal.borderStrong,
        backgroundColor: pal.premiumMuted,
      },
      proText: {
        color: pal.text,
        fontFamily: fonts.bold,
        fontSize: 11,
        letterSpacing: 0.4,
      },
      divider: {
        height: StyleSheet.hairlineWidth,
        backgroundColor: pal.divider,
        marginTop: t.spacing.xs,
      },
      telegramRow: {
        minHeight: 44,
        flexDirection: 'row',
        alignItems: 'center',
        gap: t.spacing.md,
      },
      telegramText: {
        flex: 1,
        color: pal.textMuted,
        fontFamily: fonts.semiBold,
        ...t.typography.callout,
      },
    });
  });

  return (
    <View style={[styles.root, { paddingTop: insets.top + theme.spacing.sm }]}>
      <BlurView intensity={34} tint={theme.scheme === 'dark' ? 'dark' : 'light'} style={styles.blur} />
      <LinearGradient
        pointerEvents="none"
        colors={theme.scheme === 'dark' ? ['rgba(255,255,255,0.07)', 'rgba(138,180,255,0.035)', 'transparent'] : ['rgba(255,255,255,0.92)', 'rgba(255,255,255,0.72)', 'transparent']}
        style={styles.sheen}
      />
      <View style={styles.topRow}>
        <NeptunPressable haptic={false} style={styles.brand} onPress={logoTap.onLogoTap}>
          <Text style={styles.brandTitle}>Dron Alerts</Text>
          <View style={styles.contextRow}>
            <Ionicons name={icon} size={14} color={p.textMuted} />
            <Text style={styles.contextText} numberOfLines={1}>
              {title}
            </Text>
            {onlineCount > 0 ? (
              <>
                <View style={styles.dotMuted} />
                <View style={styles.onlineDot} />
                <Text style={styles.onlineText}>{onlineCount}</Text>
              </>
            ) : null}
          </View>
        </NeptunPressable>

        <ActionChip icon="send" palette={p} styles={styles} onPress={() => void openNeptunTelegramChannel('app_bar')} />
        {showChatActions ? (
          <>
            <ActionChip icon="search" palette={p} styles={styles} onPress={() => chatChromeBridge.toggleSearch()} />
            <ActionChip icon="settings" palette={p} styles={styles} onPress={() => router.push('/chat-settings')} />
          </>
        ) : null}
        {isModerator ? (
          <ActionChip
            icon="shield-checkmark"
            tone="warning"
            palette={p}
            styles={styles}
            onPress={() => router.push('/chat-admin')}
          />
        ) : null}
        <NeptunPressable haptic style={styles.proChip} onPress={() => router.push('/premium')}>
          <Ionicons name={isPremium ? 'star' : 'ribbon'} size={17} color={isPremium ? p.premium : p.textSoft} />
          <Text style={styles.proText}>PRO</Text>
        </NeptunPressable>
        <ActionChip icon="moon-outline" palette={p} styles={styles} onPress={() => router.push('/sleep-mode')} />
      </View>

      <View style={styles.divider} />

      <NeptunPressable
        haptic={false}
        style={styles.telegramRow}
        onPress={() => void openNeptunTelegramChannel('app_bar')}
      >
        <Ionicons name="paper-plane-outline" size={18} color={p.accentSoft} />
        <Text style={styles.telegramText} numberOfLines={1}>
          Офіційний Telegram канал
        </Text>
        <Ionicons name="chevron-forward" size={20} color={p.textMuted} />
      </NeptunPressable>

      <OfflineBanner />

      <ModeratorSecretDialog
        visible={logoTap.showLogin}
        title="Модератор"
        confirmLabel="Увійти"
        onCancel={() => logoTap.setShowLogin(false)}
        onConfirm={async (secret) => {
          const err = await moderatorService.login(secret);
          if (!err) void refreshIdentity();
          return err;
        }}
      />
      <ModeratorSecretDialog
        visible={logoTap.showLogout}
        title="Модератор"
        confirmLabel="Вийти"
        destructive
        onCancel={() => logoTap.setShowLogout(false)}
        onConfirm={async () => {
          await moderatorService.logout();
          void refreshIdentity();
          return null;
        }}
      />
    </View>
  );
}

function ActionChip({
  icon,
  tone,
  palette,
  styles,
  onPress,
}: {
  icon: ComponentProps<typeof Ionicons>['name'];
  tone?: 'warning';
  palette: import('../theme/types').LegacyPalette;
  styles: { actionChip: object };
  onPress: () => void;
}) {
  return (
    <NeptunPressable haptic onPress={onPress} style={styles.actionChip}>
      <Ionicons name={icon} size={20} color={tone === 'warning' ? palette.warning : palette.textSoft} />
    </NeptunPressable>
  );
}
