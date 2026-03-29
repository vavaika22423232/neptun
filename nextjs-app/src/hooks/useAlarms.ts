'use client';

import { useState, useCallback, useRef } from 'react';
import { usePolling } from './useVisibility';
import { useAlarmSSE } from './useDataSSE';
import { HIDDEN_POLLING_INTERVAL_DESKTOP } from '@/lib/constants';
import type { Alarm } from '@/types';

// Fallback polling — 60s when active (SSE is primary), 5min when hidden
const FALLBACK_POLLING_INTERVAL = 60_000;

export function useAlarms() {
  const [alarms, setAlarms] = useState<Alarm[]>([]);
  const [alarmCount, setAlarmCount] = useState(0);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);
  const etagRef = useRef<string | null>(null);
  const inFlightRef = useRef(false);

  // Process alarm data (shared between SSE push and HTTP fetch)
  const processAlarms = useCallback((data: Alarm[]) => {
    setAlarms(data);
    setError(null);
    setLastUpdate(new Date());

    const statesWithAlarm = new Set<string>();
    data.forEach((region) => {
      if (region.activeAlerts && region.activeAlerts.length > 0) {
        if (region.regionType === 'State') {
          statesWithAlarm.add(region.regionId);
        }
      }
    });
    setAlarmCount(statesWithAlarm.size);
  }, []);

  // SSE push — instant alarm updates (primary data source)
  useAlarmSSE(processAlarms);

  // HTTP fetch — fallback polling
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

      processAlarms(data);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setError(msg);
    } finally {
      inFlightRef.current = false;
    }
  }, [processAlarms]);

  // Fallback polling: 60s active, 5min hidden (SSE is the primary source)
  usePolling(fetchAlarms, FALLBACK_POLLING_INTERVAL, HIDDEN_POLLING_INTERVAL_DESKTOP);

  return { alarms, alarmCount, lastUpdate, error, fetchAlarms };
}
