import { useQuery } from '@tanstack/react-query';
import { useFocusEffect } from 'expo-router';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { PrefsKeys } from '../../../config/prefsKeys';
import { useApp } from '../../../context/AppContext';
import { ApiError, isServerUnavailableStatus } from '../../../services/apiClient';
import { dataStreamService } from '../../../services/dataStreamService';
import { persistentStorage } from '../../../services/persistentStorage';
import { countActiveRegionsFromAlarmStream } from '../data/radarParsing';
import { radarRepository } from '../data/radarRepository';
import { groupThreatMarkersByType } from '../logic/groupThreatMarkers';
import { widgetService } from '../../widgets/services/widgetService';

/** Mirrors Flutter `radarMapHistoryMinutesProvider` / `ProGate.mapThreatHistoryMinutes`. */
export function radarHistoryMinutesForTier(isPremium: boolean): number {
  return isPremium ? 120 : 30;
}

const LIVE_POLL_MS = 30_000;
const DEGRADED_POLL_MS = 120_000;
const FOCUS_REFETCH_DEBOUNCE_MS = 2_000;

let lastRadarFocusRefetchAt = 0;

function shouldRetryRadarFetch(failureCount: number, error: unknown): boolean {
  if (error instanceof ApiError && isServerUnavailableStatus(error.status)) return false;
  return failureCount < 1;
}

function radarPollIntervalMs(query: { state: { status: string; error: unknown } }): number | false {
  if (query.state.status === 'error') {
    const err = query.state.error;
    if (err instanceof ApiError && isServerUnavailableStatus(err.status)) {
      return DEGRADED_POLL_MS;
    }
  }
  return LIVE_POLL_MS;
}

export type RadarFeedState = {
  markers: Record<string, unknown>[];
  activeOblastsUnderAlarm: number;
  groups: ReturnType<typeof groupThreatMarkersByType>;
  isLoading: boolean;
  isFetching: boolean;
  error: string | null;
  showStaleBanner: boolean;
  showTelegramRow: boolean;
  dismissTelegramRow: () => void;
  refetch: () => Promise<void>;
  lastFetchedAt: number | null;
  historyMinutes: number;
  fromDiskCache: boolean;
};

/**
 * Flutter `radar_feed_provider.dart` + `radar_tab.dart` behaviors:
 * PRO history window, stale banner, 30s poll, tab-focus refresh, SSE alarm patch.
 */
export function useRadarFeedState(): RadarFeedState {
  const { isPremium } = useApp();
  const historyMinutes = radarHistoryMinutesForTier(isPremium);
  const [alarmOverride, setAlarmOverride] = useState<number | null>(null);
  const [telegramDismissed, setTelegramDismissed] = useState(
    () => persistentStorage.getBoolean(PrefsKeys.telegramRadarBannerDismissed) ?? false,
  );
  const prevPremium = useRef(isPremium);

  const {
    data,
    error: queryError,
    isError,
    isFetching,
    isLoading,
    refetch: refetchSnapshot,
  } = useQuery({
    queryKey: ['radar', 'snapshot', historyMinutes],
    queryFn: () => radarRepository.fetchSnapshot(historyMinutes),
    staleTime: 15_000,
    refetchInterval: radarPollIntervalMs,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: false,
    retry: shouldRetryRadarFetch,
    placeholderData: (prev) => prev,
  });

  const refetch = useCallback(async () => {
    await refetchSnapshot();
  }, [refetchSnapshot]);

  useFocusEffect(
    useCallback(() => {
      const now = Date.now();
      if (now - lastRadarFocusRefetchAt < FOCUS_REFETCH_DEBOUNCE_MS) return;
      lastRadarFocusRefetchAt = now;
      void refetchSnapshot();
    }, [refetchSnapshot]),
  );

  useEffect(() => {
    if (prevPremium.current === isPremium) return;
    prevPremium.current = isPremium;
    void refetchSnapshot();
  }, [isPremium, refetchSnapshot]);

  useEffect(() => {
    const off = dataStreamService.on('alarm_update', (rows) => {
      if (!Array.isArray(rows)) return;
      const n = countActiveRegionsFromAlarmStream(rows);
      setAlarmOverride(n);
    });
    return off;
  }, []);

  const markers = data?.markers ?? [];
  const activeOblastsUnderAlarm = alarmOverride ?? data?.activeOblastsUnderAlarm ?? 0;
  const fromDiskCache = data?.fromDiskCache ?? false;
  const loading = isLoading && markers.length === 0;
  const error =
    isError && markers.length === 0
      ? queryError instanceof Error
        ? queryError.message
        : 'Помилка завантаження'
      : null;

  const showStaleBanner = fromDiskCache && markers.length > 0;

  const dismissTelegramRow = useCallback(() => {
    setTelegramDismissed(true);
    persistentStorage.setBoolean(PrefsKeys.telegramRadarBannerDismissed, true);
  }, []);

  const groups = useMemo(() => groupThreatMarkersByType(markers), [markers]);

  useEffect(() => {
    if (markers.length === 0 && activeOblastsUnderAlarm === 0) return;
    void widgetService.syncFromRadarSnapshot(markers, activeOblastsUnderAlarm);
  }, [markers, activeOblastsUnderAlarm]);

  return {
    markers,
    activeOblastsUnderAlarm,
    groups,
    isLoading: loading,
    isFetching,
    error,
    showStaleBanner,
    showTelegramRow: !telegramDismissed,
    dismissTelegramRow,
    refetch,
    lastFetchedAt: data?.fetchedAt ?? null,
    historyMinutes,
    fromDiskCache,
  };
}
