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
  const [presence, setPresence] = useState<PresenceData>({ web: 0, apps: 0, total: 0 });
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const pingPresence = useCallback(async () => {
    try {
      const userId = getUserId();
      if (!userId) return;

      const response = await fetch('/api/presence', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: userId,
          platform: 'web',
          nickname: '',
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setPresence({
          web: data.web || 0,
          apps: data.apps || data.android || 0,
          total: data.total || data.count || 0,
        });
      }
    } catch {
      // Silently fail
    }
  }, []);

  useEffect(() => {
    // Initial ping
    pingPresence();

    // Set up interval
    intervalRef.current = setInterval(pingPresence, PRESENCE_INTERVAL);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [pingPresence]);

  return presence;
}
