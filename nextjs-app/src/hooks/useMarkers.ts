'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { usePolling } from './useVisibility';
import { useMarkerSSE, useMarkerDeleteSSE, useTrackUpdateSSE } from './useDataSSE';
import { HIDDEN_POLLING_INTERVAL_DESKTOP, MARKERS_CACHE_TTL } from '@/lib/constants';
import type { Marker, BallisticThreat, TrackPosition } from '@/types';

// Fallback polling — 180s when active (SSE triggers debounced refresh), 5min hidden
const FALLBACK_POLLING_INTERVAL = 180_000;

// Debounce SSE-triggered fetches: wait 3s after last marker_new before fetching
// Prevents thundering herd: 2500 clients all fetching /api/data simultaneously
const SSE_FETCH_DEBOUNCE = 3_000;

const CACHE_KEY = 'neptun_markers_cache';

function getCachedMarkers(): Marker[] | null {
  try {
    const cached = localStorage.getItem(CACHE_KEY);
    if (!cached) return null;
    const { data, timestamp } = JSON.parse(cached);
    if (Date.now() - timestamp < MARKERS_CACHE_TTL && data?.length > 0) {
      return data;
    }
  } catch {
    // ignore
  }
  return null;
}

function setCachedMarkers(data: Marker[]) {
  try {
    if (data?.length > 0) {
      localStorage.setItem(CACHE_KEY, JSON.stringify({ data, timestamp: Date.now() }));
    } else {
      localStorage.removeItem(CACHE_KEY);
    }
  } catch {
    // ignore
  }
}

function delay(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

export function useMarkers() {
  const [markers, setMarkers] = useState<Marker[]>([]);
  const [ballisticThreat, setBallisticThreat] = useState<BallisticThreat | null>(null);
  const [serverTimeOffset, setServerTimeOffset] = useState(0); // server_time - client_time (ms)
  const etagRef = useRef<string | null>(null);
  const inFlightRef = useRef(false);
  /** Skip replacing `markers` when /api/data snapshot unchanged (less Leaflet churn). */
  const markersDataVersionRef = useRef<number | null>(null);

  // Load cached markers on mount
  useEffect(() => {
    const cached = getCachedMarkers();
    if (cached) setMarkers(cached);
  }, []);

  const fetchMarkers = useCallback(async (skipEtag = false) => {
    if (document.hidden || inFlightRef.current) return;
    inFlightRef.current = true;

    const runOnce = async (allowRetry: boolean): Promise<void> => {
      const headers: Record<string, string> = {};
      if (!skipEtag && etagRef.current) {
        headers['If-None-Match'] = etagRef.current;
      }

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 8000);

      const response = await fetch('/api/data', { headers, signal: controller.signal });
      clearTimeout(timeoutId);

      if (response.status === 304) {
        const dateHdr = response.headers.get('Date');
        if (dateHdr) {
          const serverFromDate = Date.parse(dateHdr);
          if (Number.isFinite(serverFromDate)) {
            setServerTimeOffset(serverFromDate - Date.now());
          }
        }
        return;
      }

      if (!response.ok) {
        if (allowRetry) {
          await delay(1200);
          return runOnce(false);
        }
        const cached = getCachedMarkers();
        if (cached) setMarkers(cached);
        return;
      }

      const newETag = response.headers.get('ETag');
      if (newETag) etagRef.current = newETag;

      let data: Record<string, unknown>;
      try {
        data = await response.json();
      } catch {
        if (allowRetry) {
          await delay(1200);
          return runOnce(false);
        }
        const cached = getCachedMarkers();
        if (cached) setMarkers(cached);
        return;
      }

      const items: Marker[] = Array.isArray(data.tracks)
        ? (data.tracks as Marker[])
        : Array.isArray(data.items)
          ? (data.items as Marker[])
          : [];

      const mv = typeof data.markers_version === 'number' ? data.markers_version : null;

      if (typeof data.server_time === 'number') {
        setServerTimeOffset(data.server_time - Date.now());
      }
      if (data.ballistic_threat) {
        setBallisticThreat(data.ballistic_threat as BallisticThreat);
      } else {
        setBallisticThreat(null);
      }

      const versionUnchanged = mv !== null && markersDataVersionRef.current === mv;
      if (versionUnchanged && items.length > 0) {
        return;
      }

      if (mv !== null) {
        markersDataVersionRef.current = mv;
      }

      setCachedMarkers(items);
      setMarkers(items);
    };

    try {
      await runOnce(true);
    } catch {
      const cached = getCachedMarkers();
      if (cached) setMarkers(cached);
    } finally {
      inFlightRef.current = false;
    }
  }, []);

  // SSE push — debounce: wait 3s after last marker_new before fetching
  // This prevents 2500 clients from slamming /api/data simultaneously
  const sseTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useMarkerSSE(useCallback(() => {
    if (sseTimerRef.current) clearTimeout(sseTimerRef.current);
    sseTimerRef.current = setTimeout(() => {
      sseTimerRef.current = null;
      fetchMarkers();
    }, SSE_FETCH_DEBOUNCE);
  }, [fetchMarkers]));

  // Marker delete SSE — remove immediately (no refetch, avoids stale data from other PM2 workers)
  useMarkerDeleteSSE(useCallback((deletedId: string) => {
    setMarkers((prev) => prev.filter((m) => m.id !== deletedId));
  }, []));

  // Track update SSE — apply delta directly to local state without refetch
  useTrackUpdateSSE(useCallback((data: { track_id: string; mode: string; marker: Record<string, unknown> }) => {
    const { track_id, mode, marker: markerData } = data;
    if (!track_id || !markerData) return;

    const toNum = (v: unknown): number | undefined => {
      if (typeof v === 'number' && Number.isFinite(v)) return v;
      if (typeof v === 'string' && v.trim() !== '') {
        const n = Number(v);
        return Number.isFinite(n) ? n : undefined;
      }
      return undefined;
    };

    setMarkers((prev) => {
      if (mode === 'updated') {
        const tid = String(track_id);
        const idx = prev.findIndex(
          (m) => (m.track_id != null && String(m.track_id) === tid) || String(m.id) === tid,
        );
        if (idx === -1) return prev;

        const updated = [...prev];
        const existing = { ...updated[idx] };

        const latN = toNum(markerData.lat);
        const lngN = toNum(markerData.lng);
        if (latN != null) existing.lat = latN;
        if (lngN != null) existing.lng = lngN;

        // Update other fields
        if (markerData.place) existing.place = markerData.place as string;
        if (markerData.region) existing.region = markerData.region as string;
        if (markerData.course_bearing != null) existing.course_bearing = markerData.course_bearing as number;
        if (markerData.course_direction) existing.course_direction = markerData.course_direction as string;
        if (markerData.speed_kmh != null) existing.speed_kmh = markerData.speed_kmh as number;
        if (markerData.computed_speed_kmh != null) existing.computed_speed_kmh = markerData.computed_speed_kmh as number;
        if (markerData.trajectory) existing.trajectory = markerData.trajectory as Marker['trajectory'];
        if (markerData.flight_phase) existing.flight_phase = markerData.flight_phase as Marker['flight_phase'];
        if (markerData.observation_count != null) existing.observation_count = markerData.observation_count as number;
        if (markerData.count != null) existing.count = markerData.count as number;
        if (typeof markerData.last_update_epoch === 'number') {
          existing.last_update_epoch = markerData.last_update_epoch;
        }
        if (markerData.ticker_bearing != null) {
          existing.ticker_bearing = markerData.ticker_bearing as number | null;
        }

        const positions: TrackPosition[] = existing.positions ? [...existing.positions] : [];
        if (latN != null && lngN != null) {
          const tsRaw = toNum(markerData.ts) ?? toNum(markerData.created_at_epoch) ?? Date.now();
          positions.push({
            lat: latN,
            lng: lngN,
            ts: tsRaw,
            source: (markerData.channel_name as string) || 'sse',
          });
          // Keep max 50 locally too
          if (positions.length > 50) positions.splice(0, positions.length - 50);
        }
        existing.positions = positions;

        existing.date = new Date().toISOString();
        updated[idx] = existing;
        return updated;
      }

      if (mode === 'created') {
        // New track — add marker to list
        // Use positions from broadcast if available (server sends up to 3 initial positions)
        const broadcastPositions = Array.isArray(markerData.positions)
          ? (markerData.positions as Array<Record<string, unknown>>).map((p) => ({
              lat: Number(p.lat),
              lng: Number(p.lng),
              ts: Number(p.ts) || Date.now(),
              source: (p.source as string) || 'unknown',
            }))
          : [{
              lat: markerData.lat as number,
              lng: markerData.lng as number,
              ts: (markerData.created_at_epoch as number) || Date.now(),
              source: (markerData.channel_name as string) || 'unknown',
            }];
        const newMarker: Marker = {
          id: markerData.id as string,
          track_id: track_id,
          lat: markerData.lat as number,
          lng: markerData.lng as number,
          threat_type: (markerData.threat_type as string) || 'shahed',
          place: markerData.place as string,
          region: markerData.region as string,
          text: markerData.text as string,
          date: (markerData.date as string) || new Date().toISOString(),
          count: (markerData.count as number) || 1,
          course_bearing: markerData.course_bearing as number | null,
          course_direction: markerData.course_direction as string,
          speed_kmh: markerData.speed_kmh as number,
          trajectory: markerData.trajectory as Marker['trajectory'],
          trajectory_source: markerData.trajectory_source as string,
          prediction_confidence: markerData.prediction_confidence as number,
          created_at_epoch: (markerData.created_at_epoch as number) || Date.now(),
          origin: markerData.origin as string,
          flight_phase: markerData.flight_phase as Marker['flight_phase'],
          observation_count: (markerData.observation_count as number) || 1,
          computed_speed_kmh: markerData.computed_speed_kmh as number | undefined,
          positions: broadcastPositions,
        };
        return [...prev, newMarker];
      }

      return prev;
    });
  }, []));

  // Cleanup debounce timer on unmount
  useEffect(() => {
    return () => {
      if (sseTimerRef.current) clearTimeout(sseTimerRef.current);
    };
  }, []);

  // Persist markers to localStorage cache when they change (throttled)
  const cacheTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (markers.length === 0) return;
    if (cacheTimerRef.current) clearTimeout(cacheTimerRef.current);
    cacheTimerRef.current = setTimeout(() => {
      setCachedMarkers(markers);
      cacheTimerRef.current = null;
    }, 5000); // throttle: update cache at most every 5s
    return () => {
      if (cacheTimerRef.current) clearTimeout(cacheTimerRef.current);
    };
  }, [markers]);

  // Fallback polling: 60s active, 5min hidden (SSE triggers debounced refresh)
  usePolling(fetchMarkers, FALLBACK_POLLING_INTERVAL, HIDDEN_POLLING_INTERVAL_DESKTOP);

  // Force refresh — clears ETag, waits for nginx cache to expire, then fetches
  const forceRefreshMarkers = useCallback(async () => {
    etagRef.current = null;
    // Wait for nginx API_CACHE to expire (3s cache + margin)
    await new Promise((r) => setTimeout(r, 3500));
    inFlightRef.current = false; // ensure not blocked
    await fetchMarkers(true);
  }, [fetchMarkers]);

  return { markers, ballisticThreat, fetchMarkers, forceRefreshMarkers, serverTimeOffset };
}
