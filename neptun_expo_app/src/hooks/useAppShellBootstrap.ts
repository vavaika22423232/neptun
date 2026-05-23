import { useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { dataStreamService } from '../services/dataStreamService';
import { moderatorService } from '../services/moderatorService';
import { presenceService } from '../services/presenceService';
import { adService, bindAdAppStateListener } from '../services/adService';
import { entitlementsService } from '../services/entitlementsService';
import { purchaseService } from '../services/purchaseService';

function parseOnline(payload: unknown): number | null {
  if (payload == null) return null;
  if (typeof payload === 'number' && Number.isFinite(payload)) return Math.floor(payload);
  if (typeof payload === 'string') {
    const n = Number(payload);
    return Number.isFinite(n) ? Math.floor(n) : null;
  }
  if (typeof payload === 'object') {
    const obj = payload as Record<string, unknown>;
    const raw = obj.count ?? obj.online ?? obj.total;
    if (typeof raw === 'number' && Number.isFinite(raw)) return Math.floor(raw);
    if (typeof raw === 'string') {
      const n = Number(raw);
      return Number.isFinite(n) ? Math.floor(n) : null;
    }
  }
  return null;
}

/**
 * Mirrors Flutter `AppShell.initState`: SSE, presence, moderator init, purchase entitlement.
 */
export function useAppShellBootstrap(): void {
  const { setOnlineCount } = useApp();

  useEffect(() => {
    void moderatorService.init();
    void (async () => {
      await entitlementsService.bootstrap();
      await purchaseService.initialize();
      await adService.initialize();
      adService.markSessionActive();
    })();
    const unbindAds = bindAdAppStateListener();

    let presenceTotal: number | null = null;
    let chatOnline = 0;

    const publishOnline = () => {
      setOnlineCount(presenceTotal ?? chatOnline);
    };

    presenceService.start();
    const unsubPresence = presenceService.subscribe((total) => {
      presenceTotal = total;
      publishOnline();
    });

    dataStreamService.connect();
    const unsubOnline = dataStreamService.on('online', (payload) => {
      const count = parseOnline(payload);
      if (count != null) {
        chatOnline = count;
        publishOnline();
      }
    });
    const unsubConnected = dataStreamService.on('connected', (payload) => {
      const count = parseOnline(payload);
      if (count != null) {
        chatOnline = count;
        publishOnline();
      }
    });

    publishOnline();

    return () => {
      unbindAds();
      unsubPresence();
      unsubOnline();
      unsubConnected();
      presenceService.stop();
      dataStreamService.disconnect();
    };
  }, [setOnlineCount]);
}
