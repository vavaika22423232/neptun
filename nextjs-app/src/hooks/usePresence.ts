'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { PRESENCE_INTERVAL, PRESENCE_DISPLAY_POLL_MS } from '@/lib/constants';
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

export function usePresence() {
  const [presence, setPresence] = useState<PresenceData>({ web: 0, apps: 0, total: -1 });
  const heartbeatRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const displayPollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const failCountRef = useRef(0);

  const applyPresencePayload = useCallback((data: Record<string, unknown>) => {
    setPresence({
      web: Number(data.web) || 0,
      apps: Number(data.apps ?? data.android) || 0,
      total: Number(data.total ?? data.count) || 0,
    });
  }, []);

  /** Рідкий POST — залишаємо користувача в sorted set. */
  const pingPresence = useCallback(async () => {
    if (typeof document !== 'undefined' && document.visibilityState === 'hidden') return;

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

  /** Частий GET — лише оновлення числа в інтерфейсі без чергового ZADD. */
  const pollPresenceDisplay = useCallback(async () => {
    if (typeof document !== 'undefined' && document.visibilityState === 'hidden') return;

    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 8000);
      const response = await fetch('/api/presence', {
        method: 'GET',
        signal: controller.signal,
      });
      clearTimeout(timeout);
      if (response.ok) {
        const data = (await response.json()) as Record<string, unknown>;
        failCountRef.current = 0;
        applyPresencePayload(data);
      }
    } catch {
      /* не чіпаємо failCount — heartbeat відповідає за «офлайн» індикатор */
    }
  }, [applyPresencePayload]);

  useEffect(() => {
    void pingPresence();
    void pollPresenceDisplay();
    heartbeatRef.current = setInterval(() => {
      void pingPresence();
    }, PRESENCE_INTERVAL);
    displayPollRef.current = setInterval(() => {
      void pollPresenceDisplay();
    }, PRESENCE_DISPLAY_POLL_MS);
    return () => {
      if (heartbeatRef.current) clearInterval(heartbeatRef.current);
      if (displayPollRef.current) clearInterval(displayPollRef.current);
    };
  }, [pingPresence, pollPresenceDisplay]);

  return presence;
}
