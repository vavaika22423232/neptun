import { useRouter } from 'expo-router';
import type { ComponentProps } from 'react';
import { memo, useCallback, useMemo } from 'react';
import { View } from 'react-native';
import { openNeptunTelegramChannel } from '../core/utils/openNeptunTelegram';
import { useModeratorLogoTap } from '../core/moderator/useModeratorLogoTap';
import { ModeratorSecretDialog } from '../features/chat/components/ModeratorSecretDialog';
import { chatChromeBridge } from '../features/chat/chatChromeBridge';
import { useApp } from '../context/AppContext';
import { moderatorService } from '../services/moderatorService';
import { useAppTheme } from '../theme/useAppTheme';
import { useMapStore } from '../features/map/state/mapStore';
import { relativeTimeUk } from '../features/map/utils/relativeTimeUk';
import { OfflineBanner } from './OfflineBanner';
import { AppScreenHeader } from './ui/AppScreenHeader';
import { HeaderActionButton } from './ui/HeaderActionButton';
import { HeaderProPill } from './ui/HeaderProPill';

type TabKey = 'index' | 'radar' | 'chat' | 'profile' | 'regions' | string;

const TAB_META: Record<
  string,
  { title: string; icon: ComponentProps<typeof import('@expo/vector-icons').Ionicons>['name'] }
> = {
  index: { title: 'Live', icon: 'pulse-outline' },
  radar: { title: 'Radar', icon: 'radio-outline' },
  chat: { title: 'Community', icon: 'chatbubble-outline' },
  profile: { title: 'You', icon: 'person-outline' },
  regions: { title: 'Регіони', icon: 'notifications-outline' },
};

function mapSubtitle(linkPhase: string, lastRefresh?: number): string {
  switch (linkPhase) {
    case 'idle':
      return 'Підготовка живих даних';
    case 'connecting':
      return 'Підключення до каналу…';
    case 'reconnecting':
    case 'offline':
      return 'Відновлюємо канал даних…';
    case 'live':
      if (!lastRefresh) return 'Канал активний';
      return `Оновлено · ${relativeTimeUk(new Date(lastRefresh))}`;
    default:
      return 'Жива ситуація навколо вас';
  }
}

type Props = {
  routeName: TabKey;
};

function MainTabChromeInner({ routeName }: Props) {
  const router = useRouter();
  const { onlineCount, isPremium, isModerator, refreshIdentity } = useApp();
  const { theme, setMode } = useAppTheme();
  const logoTap = useModeratorLogoTap();
  const linkPhase = useMapStore((s) => s.linkPhase);
  const lastRefresh = useMapStore((s) => s.lastSignificantRefreshAt);

  const meta = TAB_META[routeName] ?? { title: routeName, icon: 'ellipse-outline' as const };

  const onThemePress = useCallback(() => {
    setMode(theme.scheme === 'dark' ? 'light' : 'dark');
  }, [setMode, theme.scheme]);

  const onTelegram = useCallback(() => {
    void openNeptunTelegramChannel(routeName === 'radar' ? 'radar_header' : 'app_bar');
  }, [routeName]);

  const themeIcon =
    theme.scheme === 'dark' ? ('sunny-outline' as const) : ('moon-outline' as const);

  const subtitle = useMemo(() => {
    if (routeName === 'index') return mapSubtitle(linkPhase, lastRefresh);
    if (routeName === 'radar') {
      return onlineCount > 0 ? `${onlineCount} активних оновлень` : 'Стрічка подій та інсайтів';
    }
    if (routeName === 'chat') {
      return onlineCount > 0 ? `${onlineCount} онлайн · спільнота NEPTUN` : 'Розмови, правила та модерація';
    }
    if (routeName === 'profile') {
      return isPremium ? 'PRO активний · ваш центр' : 'Регіони, сповіщення, безпека';
    }
    return undefined;
  }, [routeName, linkPhase, lastRefresh, onlineCount, isPremium]);

  const isLive =
    (routeName === 'radar' || routeName === 'chat') && onlineCount > 0;

  const actions = useMemo(() => {
    const nodes = [
      <HeaderActionButton
        key="tg"
        icon="paper-plane-outline"
        tone="telegram"
        accessibilityLabel="Telegram"
        onPress={onTelegram}
      />,
    ];

    if (routeName === 'index') {
      nodes.push(
        <HeaderActionButton
          key="regions"
          icon="notifications-outline"
          accessibilityLabel="Регіони"
          onPress={() => router.push('/regions')}
        />,
      );
    }

    if (routeName === 'chat') {
      nodes.push(
        <HeaderActionButton
          key="search"
          icon="search-outline"
          accessibilityLabel="Пошук"
          onPress={() => chatChromeBridge.toggleSearch()}
        />,
        <HeaderActionButton
          key="settings"
          icon="settings-outline"
          accessibilityLabel="Налаштування чату"
          onPress={() => router.push('/chat-settings')}
        />,
      );
    }

    if (routeName === 'radar') {
      if (isModerator) {
        nodes.push(
          <HeaderActionButton
            key="mod"
            icon="shield-checkmark"
            tone="warning"
            accessibilityLabel="Модератор"
            onPress={() => router.push('/chat-admin')}
          />,
        );
      } else {
        nodes.push(
          <HeaderActionButton
            key="safety"
            icon="shield-outline"
            accessibilityLabel="Безпека"
            onPress={() => router.push('/safety')}
          />,
        );
      }
    } else if (isModerator) {
      nodes.push(
        <HeaderActionButton
          key="mod"
          icon="shield-checkmark"
          tone="warning"
          accessibilityLabel="Модератор"
          onPress={() => router.push('/chat-admin')}
        />,
      );
    }

    if (routeName === 'profile') {
      nodes.push(
        <HeaderActionButton
          key="help"
          icon="help-circle-outline"
          accessibilityLabel="Підтримка"
          onPress={() => router.push('/trust')}
        />,
      );
    }

    nodes.push(
      <HeaderProPill key="pro" isPremium={isPremium} onPress={() => router.push('/premium')} />,
      <HeaderActionButton
        key="theme"
        icon={themeIcon}
        accessibilityLabel="Тема"
        onPress={onThemePress}
      />,
    );

    return nodes;
  }, [routeName, isModerator, isPremium, onTelegram, onThemePress, router, themeIcon]);

  const showTelegramFooter = routeName !== 'profile';

  return (
    <View>
      <AppScreenHeader
        title={meta.title}
        titleIcon={meta.icon}
        subtitle={subtitle}
        liveCount={onlineCount}
        isLive={isLive}
        actions={actions}
        showTelegramFooter={showTelegramFooter}
        onBrandPress={logoTap.onLogoTap}
        onTelegramPress={showTelegramFooter ? onTelegram : undefined}
      />
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

export const MainTabChrome = memo(MainTabChromeInner);
