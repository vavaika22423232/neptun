'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { PRESENCE_INTERVAL } from '@/lib/constants';
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
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const failCountRef = useRef(0);

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
        const data = await response.json();
        failCountRef.current = 0;
        setPresence({
          web: data.web || 0,
          apps: data.apps || data.android || 0,
          total: data.total || data.count || 0,
        });
      } else {
        failCountRef.current++;
      }
    } catch {
      failCountRef.current++;
    }

    if (failCountRef.current >= 3) {
      setPresence(prev => ({ ...prev, total: -1 }));
    }
  }, []);

  useEffect(() => {
    pingPresence();
    intervalRef.current = setInterval(pingPresence, PRESENCE_INTERVAL);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [pingPresence]);

  return presence;
}
