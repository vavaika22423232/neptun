'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import {
  PRESENCE_INTERVAL,
  PRESENCE_BACKGROUND_INTERVAL,
  PRESENCE_DISPLAY_POLL_MS,
} from '@/lib/constants';
import type { PresenceData } from '@/types';

function getUserId(): string {
  if (typeof window === 'undefined') return '';
  let userId = localStorage.getItem('neptun_uid');
  if (!userId) {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    userId = 'U';
    for (let i = 0; i < 7; i++) {
      userId += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    localStorage.setItem('neptun_uid', userId);
  }
  return userId;
}

function isEmbedPresencePage(): boolean {
  if (typeof document === 'undefined') return false;
  return document.documentElement.classList.contains('embed-mode');
}

/** Інтервал heartbeat: вкладка у фоні пінгує рідше, але не зникає з «онлайн». */
function presenceHeartbeatDelayMs(): number {
  if (isEmbedPresencePage()) return PRESENCE_INTERVAL;
  if (typeof document !== 'undefined' && document.visibilityState === 'hidden') {
    return PRESENCE_BACKGROUND_INTERVAL;
  }
  return PRESENCE_INTERVAL;
}

export function usePresence() {
  const [presence, setPresence] = useState<PresenceData>({ web: 0, apps: 0, total: -1 });
  const heartbeatTimerRef = useRef<number | null>(null);
  const displayPollRef = useRef<number | null>(null);
  const failCountRef = useRef(0);
  const pingPresenceRef = useRef<() => Promise<void>>(async () => {});

  const applyPresencePayload = useCallback((data: Record<string, unknown>) => {
    setPresence({
      web: Number(data.web) || 0,
      apps: Number(data.apps ?? data.android) || 0,
      total: Number(data.total ?? data.count) || 0,
    });
  }, []);

  /** POST — оновлює score у Redis (користувач лишається в сесії). */
  const pingPresence = useCallback(async () => {
    try {
      const userId = getUserId();
      if (!userId) return;

      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 8000);

      const response = await fetch('/api/presence', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: userId, platform: 'web', nickname: '' }),
        signal: controller.signal,
        keepalive: true,
      });
      clearTimeout(timeout);

      if (response.ok) {
        const data = (await response.json()) as Record<string, unknown>;
        failCountRef.current = 0;
        applyPresencePayload(data);
      } else {
        failCountRef.current++;
      }
    } catch {
      failCountRef.current++;
    }

    if (failCountRef.current >= 3) {
      setPresence((prev) => ({ ...prev, total: -1 }));
    }
  }, [applyPresencePayload]);

  pingPresenceRef.current = pingPresence;

  /** GET — лише оновлення числа в HUD (працює і у фоновій вкладці). */
  const pollPresenceDisplay = useCallback(async () => {
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 8000);
      const response = await fetch('/api/presence', {
        method: 'GET',
        signal: controller.signal,
        cache: 'no-store',
      });
      clearTimeout(timeout);
      if (response.ok) {
        const data = (await response.json()) as Record<string, unknown>;
        failCountRef.current = 0;
        applyPresencePayload(data);
      }
    } catch {
      /* heartbeat відповідає за «офлайн» індикатор */
    }
  }, [applyPresencePayload]);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const clearHeartbeat = () => {
      if (heartbeatTimerRef.current != null) {
        window.clearTimeout(heartbeatTimerRef.current);
        heartbeatTimerRef.current = null;
      }
    };

    const scheduleHeartbeat = () => {
      clearHeartbeat();
      heartbeatTimerRef.current = window.setTimeout(() => {
        void pingPresenceRef.current().finally(scheduleHeartbeat);
      }, presenceHeartbeatDelayMs());
    };

    const onVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        void pingPresenceRef.current();
      }
      scheduleHeartbeat();
    };

    const onPageHide = () => {
      const userId = getUserId();
      if (!userId || typeof navigator.sendBeacon !== 'function') return;
      try {
        const body = JSON.stringify({ id: userId, platform: 'web', nickname: '' });
        const blob = new Blob([body], { type: 'application/json' });
        navigator.sendBeacon('/api/presence', blob);
      } catch {
        /* ignore */
      }
    };

    void pingPresenceRef.current();
    scheduleHeartbeat();
    void pollPresenceDisplay();

    displayPollRef.current = window.setInterval(() => {
      void pollPresenceDisplay();
    }, PRESENCE_DISPLAY_POLL_MS);

    document.addEventListener('visibilitychange', onVisibilityChange);
    window.addEventListener('pagehide', onPageHide);

    return () => {
      clearHeartbeat();
      if (displayPollRef.current != null) {
        window.clearInterval(displayPollRef.current);
        displayPollRef.current = null;
      }
      document.removeEventListener('visibilitychange', onVisibilityChange);
      window.removeEventListener('pagehide', onPageHide);
    };
  }, [pollPresenceDisplay]);

  return presence;
}
