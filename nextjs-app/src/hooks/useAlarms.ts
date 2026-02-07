'use client';

import { useState, useCallback, useRef } from 'react';
import { usePolling } from './useVisibility';
import { ACTIVE_POLLING_INTERVAL, HIDDEN_POLLING_INTERVAL_DESKTOP } from '@/lib/constants';
import type { Alarm } from '@/types';

export function useAlarms() {
  const [alarms, setAlarms] = useState<Alarm[]>([]);
  const [alarmCount, setAlarmCount] = useState(0);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);
  const etagRef = useRef<string | null>(null);
  const inFlightRef = useRef(false);

  const fetchAlarms = useCallback(async () => {
    if (document.hidden || inFlightRef.current) return;
    inFlightRef.current = true;

    try {
      const headers: Record<string, string> = {};
      if (etagRef.current) {
        headers['If-None-Match'] = etagRef.current;
      }

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 8000);

      const response = await fetch('/api/alarms/all', {
        headers,
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      if (response.status === 304) return; // Unchanged
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const newETag = response.headers.get('ETag');
      if (newETag) etagRef.current = newETag;

      const data: Alarm[] = await response.json();
      if (!Array.isArray(data)) throw new Error('Invalid data format');

      setAlarms(data);
      setError(null);
      setLastUpdate(new Date());

      // Count unique states with alarms
      const statesWithAlarm = new Set<string>();
      data.forEach((region) => {
        if (region.activeAlerts && region.activeAlerts.length > 0) {
          if (region.regionType === 'State') {
            statesWithAlarm.add(region.regionId);
          }
        }
      });
      setAlarmCount(statesWithAlarm.size);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setError(msg);
    } finally {
      inFlightRef.current = false;
    }
  }, []);

  usePolling(fetchAlarms, ACTIVE_POLLING_INTERVAL, HIDDEN_POLLING_INTERVAL_DESKTOP);

  return { alarms, alarmCount, lastUpdate, error, fetchAlarms };
}
