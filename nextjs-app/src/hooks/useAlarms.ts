'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { usePolling } from './useVisibility';
import { useAlarmSSE } from './useDataSSE';
import { HIDDEN_POLLING_INTERVAL_DESKTOP } from '@/lib/constants';
import { isOblastLevelAlarm } from '@/lib/map/alarm-hasc-filter';
import type { Alarm } from '@/types';

// Fallback polling — 60s when active (SSE is primary), 5min when hidden
const FALLBACK_POLLING_INTERVAL = 60_000;

function countStateAlarms(data: Alarm[]): number {
  const statesWithAlarm = new Set<string>();
  data.forEach((region) => {
    if (isOblastLevelAlarm(region)) {
      statesWithAlarm.add(region.regionId);
    }
  });
  return statesWithAlarm.size;
}

export type UseAlarmsOptions = {
  /** From SSR (`getInitialAlarmsSnapshot`) — same cache as GET /api/alarms/all */
  initialAlarms?: Alarm[];
  initialEtag?: string | null;
};

export function useAlarms(options?: UseAlarmsOptions) {
  const seed = options?.initialAlarms ?? [];
  const [alarms, setAlarms] = useState<Alarm[]>(seed);
  const [alarmCount, setAlarmCount] = useState(() => countStateAlarms(seed));
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);
  const etagRef = useRef<string | null>(options?.initialEtag ?? null);
  const inFlightRef = useRef(false);

  // Process alarm data (shared between SSE push and HTTP fetch)
  const processAlarms = useCallback((data: Alarm[]) => {
    setAlarms(data);
    setError(null);
    setLastUpdate(new Date());

    setAlarmCount(countStateAlarms(data));
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

  // React Strict Mode (dev) remounts before the first fetch finishes: `inFlightRef` stays true,
  // the remount's immediate poll bails out, and `setState` from the abandoned fetch is dropped —
  // UI stays empty until the next 60s interval. Reset the guard on unmount so a new mount can fetch.
  useEffect(
    () => () => {
      inFlightRef.current = false;
    },
    [],
  );

  // Fallback polling: 60s active, 5min hidden (SSE is the primary source)
  usePolling(fetchAlarms, FALLBACK_POLLING_INTERVAL, HIDDEN_POLLING_INTERVAL_DESKTOP);

  return { alarms, alarmCount, lastUpdate, error, fetchAlarms };
}
