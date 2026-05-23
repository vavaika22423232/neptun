import { useRouter } from 'expo-router';
import { memo, useMemo } from 'react';
import { View } from 'react-native';
import { openNeptunTelegramChannel } from '../../../core/utils/openNeptunTelegram';
import { useModeratorLogoTap } from '../../../core/moderator/useModeratorLogoTap';
import { OfflineBanner } from '../../../components/OfflineBanner';
import { ModeratorSecretDialog } from '../../chat/components/ModeratorSecretDialog';
import { useApp } from '../../../context/AppContext';
import { moderatorService } from '../../../services/moderatorService';
import { relativeTimeUk } from '../../map/utils/relativeTimeUk';
import { useRadarFeedState } from '../hooks/useRadarFeedState';
import { useStreamLive } from '../hooks/useStreamLive';
import { useRadarStore } from '../store/radarStore';
import type { ConnectionStatus } from '../types/radar.types';
import { RadarTabHeader } from './RadarTabHeader';

function mapConnection(status: ConnectionStatus): 'online' | 'connecting' | 'offline' {
  if (status === 'live') return 'online';
  if (status === 'offline') return 'offline';
  return 'connecting';
}

function connLabel(status: 'online' | 'connecting' | 'offline'): string {
  if (status === 'online') return 'онлайн';
  if (status === 'connecting') return 'зʼєднання…';
  return 'офлайн';
}

function RadarTabChromeInner() {
  const router = useRouter();
  const { isModerator, refreshIdentity } = useApp();
  const logoTap = useModeratorLogoTap();
  const feed = useRadarFeedState();
  const streamStatus = useStreamLive(feed.showStaleBanner);
  const toggleSearch = useRadarStore((s) => s.toggleSearch);

  const connectionStatus = useMemo(() => mapConnection(streamStatus), [streamStatus]);
  const isLive = connectionStatus === 'online';

  const statusLine = useMemo(() => {
    const count = feed.markers.length;
    const events =
      count === 0 ? 'немає активних' : count === 1 ? '1 подія' : `${count} подій`;
    const conn = connLabel(connectionStatus);
    const updated = feed.lastFetchedAt
      ? relativeTimeUk(new Date(feed.lastFetchedAt))
      : null;
    return updated ? `${events} · ${conn} · ${updated}` : `${events} · ${conn}`;
  }, [connectionStatus, feed.lastFetchedAt, feed.markers.length]);

  return (
    <View>
      <RadarTabHeader
        isLive={isLive}
        statusLine={statusLine}
        showModeratorAction={isModerator}
        onBrandPress={logoTap.onLogoTap}
        onSearchPress={toggleSearch}
        onTelegramPress={() => void openNeptunTelegramChannel('radar_header')}
        onModeratorPress={() => router.push('/chat-admin')}
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

export const RadarTabChrome = memo(RadarTabChromeInner);
