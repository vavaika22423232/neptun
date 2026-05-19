'use client';

import { useState, useCallback, useRef, useEffect, useLayoutEffect } from 'react';
import { usePolling } from './useVisibility';
import { useMarkerSSE, useMarkerDeleteSSE, useTrackUpdateSSE } from './useDataSSE';
import { API_DATA_PUBLIC_QUERY, HIDDEN_POLLING_INTERVAL_DESKTOP, MARKERS_CACHE_TTL } from '@/lib/constants';
import type { Marker, BallisticThreat, TrackPosition } from '@/types';
import {
  computeMarkerDisplayPolicy,
  DEFAULT_MARKER_DISPLAY_POLICY,
  isOffshoreOrMaritimeResolve,
} from '@/lib/marker-display-policy';

// Fallback polling — SSE is primary, but keep the backup tight enough for active threat mode.
const FALLBACK_POLLING_INTERVAL = 30_000;

// Debounce SSE-triggered snapshot fetches. Marker payloads are applied immediately;
// this is only a consistency refresh for burst / legacy events.
const SSE_FETCH_DEBOUNCE = 500;

const CACHE_KEY = 'neptun_markers_cache';
// Boot cache is only for a fast first paint. Mobile/WebView tabs can start as
// hidden, so an old localStorage snapshot must never replace a fresh server load.
const BOOT_CACHE_MAX_AGE = 90_000;
const FRESH_CLIENT_MARKER_GRACE_MS = 90_000;

/** Prefer server display_* from SSE (matches /api/data); else local policy with defaults. */
function applyDisplayPolicyFromSsePayload(target: Marker, markerData: Record<string, unknown>): void {
  const dc = markerData.display_class;
  const sp = markerData.show_precise_pin;
  if (typeof dc === 'string' && typeof sp === 'boolean') {
    target.display_class = dc as NonNullable<Marker['display_class']>;
    target.show_precise_pin = sp;
    if (typeof markerData.display_uncertainty_km === 'number' && Number.isFinite(markerData.display_uncertainty_km)) {
      target.display_uncertainty_km = markerData.display_uncertainty_km;
    }
    if (typeof markerData.display_trust_hint_uk === 'string') {
      target.display_trust_hint_uk = markerData.display_trust_hint_uk;
    }
    // `resolve_status` may be fresher than stale server `display_*` in SSE — re-apply policy for offshore/maritime.
    if (isOffshoreOrMaritimeResolve(target)) {
      Object.assign(target, computeMarkerDisplayPolicy(target, DEFAULT_MARKER_DISPLAY_POLICY));
    }
    return;
  }
  if (
    target.display_class &&
    typeof target.show_precise_pin === 'boolean' &&
    typeof target.display_uncertainty_km === 'number'
  ) {
    return;
  }
  Object.assign(target, computeMarkerDisplayPolicy(target, DEFAULT_MARKER_DISPLAY_POLICY));
}

function normalizeEpochMs(ts: unknown): number {
  const n = typeof ts === 'number' ? ts : Number(ts);
  if (!Number.isFinite(n) || n <= 0) return Date.now();
  return n > 10_000_000_000 ? n : n * 1000;
}

function normalizeTrackPoints(points: Array<Record<string, unknown>>): TrackPosition[] {
  return points.map((p) => {
    const ts = Number(p.ts) || Date.now();
    return {
      lat: Number(p.lat),
      lng: Number(p.lng),
      ts: ts > 10_000_000_000 ? ts : ts * 1000,
      source: (p.source as string) || 'sse',
      ...(typeof p.reason === 'string' ? { reason: p.reason } : {}),
      ...(typeof p.confidence === 'number' ? { confidence: p.confidence } : {}),
    };
  });
}

function applyTrackLifecycleFromPayload(target: Marker, markerData: Record<string, unknown>): void {
  if (typeof markerData.track_state === 'string') {
    target.track_state = markerData.track_state as Marker['track_state'];
  }
  if (typeof markerData.track_confidence === 'number' && Number.isFinite(markerData.track_confidence)) {
    target.track_confidence = markerData.track_confidence;
  }
  if (typeof markerData.motion_reason === 'string') {
    target.motion_reason = markerData.motion_reason;
  }
  if (typeof markerData.last_observation_epoch === 'number') {
    target.last_observation_epoch = markerData.last_observation_epoch;
  }
  if (Array.isArray(markerData.rejected_observations)) {
    target.rejected_observations = normalizeTrackPoints(
      markerData.rejected_observations as Array<Record<string, unknown>>,
    ) as Marker['rejected_observations'];
  }
}

function getCachedMarkers(maxAgeMs = MARKERS_CACHE_TTL): Marker[] | null {
  try {
    const cached = localStorage.getItem(CACHE_KEY);
    if (!cached) return null;
    const { data, timestamp } = JSON.parse(cached);
    if (Date.now() - timestamp < maxAgeMs && data?.length > 0) {
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

function markerIdentity(marker: Pick<Marker, 'id' | 'track_id' | 'lat' | 'lng' | 'threat_type'>): string {
  const tid = marker.track_id != null && String(marker.track_id).trim().length > 0 ? String(marker.track_id).trim() : '';
  if (tid) return `t:${tid}`;
  const id = marker.id != null && String(marker.id).trim().length > 0 ? String(marker.id).trim() : '';
  if (id) return `i:${id}`;
  const lat = Number(marker.lat);
  const lng = Number(marker.lng);
  if (Number.isFinite(lat) && Number.isFinite(lng)) {
    return `p:${lat.toFixed(3)}_${lng.toFixed(3)}_${marker.threat_type || 'x'}`;
  }
  return '';
}

function mergeSnapshotWithFreshClientMarkers(snapshot: Marker[], previous: Marker[], nowMs = Date.now()): Marker[] {
  if (previous.length === 0) return snapshot;

  const snapshotKeys = new Set(snapshot.map(markerIdentity).filter(Boolean));
  const merged = [...snapshot];

  for (const marker of previous) {
    const key = markerIdentity(marker);
    if (!key || snapshotKeys.has(key)) continue;

    const lastUpdate = normalizeEpochMs(
      marker.last_update_epoch ??
      marker.last_observation_epoch ??
      marker.created_at_epoch ??
      marker.date,
    );
    if (nowMs - lastUpdate <= FRESH_CLIENT_MARKER_GRACE_MS) {
      merged.push(marker);
      snapshotKeys.add(key);
    }
  }

  return merged;
}

function readInitialMarkers(): Marker[] {
  if (typeof window === 'undefined') return [];
  try {
    return getCachedMarkers(BOOT_CACHE_MAX_AGE) ?? [];
  } catch {
    return [];
  }
}

export type UseMarkersBootstrap = {
  markers: Marker[];
  markersVersion: number | null;
  serverTime: number | null;
  ballisticThreat: BallisticThreat | null;
};

export function useMarkers(bootstrap?: UseMarkersBootstrap) {
  /** SSR snapshot first, else localStorage — both synchronous before first paint. */
  const [markers, setMarkers] = useState<Marker[]>(() => {
    if (bootstrap?.markers && bootstrap.markers.length > 0) return bootstrap.markers;
    return readInitialMarkers();
  });
  /** Sync length for fetch gating without widening fetchMarkers deps (avoids polling storms). */
  const markerCountRef = useRef(0);
  const [ballisticThreat, setBallisticThreat] = useState<BallisticThreat | null>(
    () => bootstrap?.ballisticThreat ?? null,
  );
  const [serverTimeOffset, setServerTimeOffset] = useState(0); // server_time - client_time (ms)
  const etagRef = useRef<string | null>(null);
  const inFlightRef = useRef(false);
  const hasFetchedSnapshotRef = useRef(false);
  /** Skip replacing `markers` when /api/data snapshot unchanged (less Leaflet churn). */
  const markersDataVersionRef = useRef<number | null>(null);

  useLayoutEffect(() => {
    if (bootstrap?.markersVersion != null && Number.isFinite(bootstrap.markersVersion)) {
      markersDataVersionRef.current = bootstrap.markersVersion;
    }
    if (bootstrap?.markers && bootstrap.markers.length > 0) {
      setCachedMarkers(bootstrap.markers);
    }
    if (typeof bootstrap?.serverTime === 'number' && Number.isFinite(bootstrap.serverTime)) {
      setServerTimeOffset(bootstrap.serverTime - Date.now());
    }
  }, [bootstrap]);

  useLayoutEffect(() => {
    markerCountRef.current = markers.length;
  }, [markers]);

  const fetchMarkers = useCallback(async (skipEtag = false, force = false) => {
    // Flutter / in-app WebViews often keep `document.hidden === true` even while the map is on screen,
    // which previously skipped every poll and left markers empty forever.
    const embedPage =
      typeof document !== 'undefined' &&
      document.documentElement.classList.contains('embed-mode');
    // Mobile Safari / Chrome sometimes report `document.hidden === true` on the first paint after navigation.
    // If we skip HTTP fetch while hidden AND have zero markers, the map stays empty until reload or SSE debounce.
    const hasAnyMarkers = markerCountRef.current > 0;
    const hasFetchedSnapshot = hasFetchedSnapshotRef.current;
    if (!force && hasFetchedSnapshot && document.hidden && !embedPage && hasAnyMarkers) return;
    if (inFlightRef.current) return;
    inFlightRef.current = true;

    const runOnce = async (allowRetry: boolean, after304Retry = false): Promise<void> => {
      const headers: Record<string, string> = {};
      if (!skipEtag && etagRef.current) {
        headers['If-None-Match'] = etagRef.current;
      }

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 8000);

      const response = await fetch(`/api/data?${API_DATA_PUBLIC_QUERY}`, {
        headers,
        signal: controller.signal,
        priority: 'high',
        cache: 'no-store',
      });
      clearTimeout(timeoutId);

      if (response.status === 304) {
        hasFetchedSnapshotRef.current = true;
        const dateHdr = response.headers.get('Date');
        if (dateHdr) {
          const serverFromDate = Date.parse(dateHdr);
          if (Number.isFinite(serverFromDate)) {
            setServerTimeOffset(serverFromDate - Date.now());
          }
        }
        // 304 has no body — if we still have zero markers (cold navigation, multi-worker ETag oddity),
        // drop ETag and do one full read.
        if (markerCountRef.current === 0 && !after304Retry) {
          etagRef.current = null;
          return runOnce(allowRetry, true);
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
      if (!force && versionUnchanged && items.length > 0 && markerCountRef.current > 0) {
        hasFetchedSnapshotRef.current = true;
        return;
      }

      if (mv !== null) {
        markersDataVersionRef.current = mv;
      }

      hasFetchedSnapshotRef.current = true;
      setMarkers((prev) => {
        const merged = mergeSnapshotWithFreshClientMarkers(items, prev);
        setCachedMarkers(merged);
        return merged;
      });
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

  // Mobile Safari / Android WebView can delay timers, preserve an old BFCache
  // page, or report hidden on first paint. Always force a fresh snapshot around
  // boot and when the page becomes active again.
  useEffect(() => {
    if (typeof window === 'undefined') return;

    let cancelled = false;
    const refresh = () => {
      if (!cancelled) void fetchMarkers(true, true);
    };
    const refreshIfEmpty = () => {
      if (!cancelled && markerCountRef.current === 0) void fetchMarkers(true, true);
    };
    const handleVisibilityChange = () => {
      if (!document.hidden) refresh();
    };
    const handlePageShow = (ev: Event) => {
      if ((ev as PageTransitionEvent).persisted) {
        etagRef.current = null;
      }
      refresh();
    };

    refresh();
    const instantEmptyRetry = window.setTimeout(refreshIfEmpty, 250);
    const bootRetrySoon = window.setTimeout(() => {
      if (!cancelled && markerCountRef.current === 0) refresh();
    }, 400);
    const shortRetry = window.setTimeout(refresh, 1500);
    const emptyRetry = window.setTimeout(refreshIfEmpty, 8000);

    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('pageshow', handlePageShow);
    window.addEventListener('focus', refresh);

    return () => {
      cancelled = true;
      window.clearTimeout(instantEmptyRetry);
      window.clearTimeout(bootRetrySoon);
      window.clearTimeout(shortRetry);
      window.clearTimeout(emptyRetry);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('pageshow', handlePageShow);
      window.removeEventListener('focus', refresh);
    };
  }, [fetchMarkers]);

  // Server pushes `markers_version` on SSE connect + keepalive (`markers_sync`); reconcile if drift.
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const onVersionSync = (ev: Event) => {
      const d = (ev as CustomEvent<{ markers_version?: number }>).detail;
      const v = d?.markers_version;
      if (typeof v !== 'number' || !Number.isFinite(v)) return;
      if (markersDataVersionRef.current != null && markersDataVersionRef.current === v) return;
      void fetchMarkers(true, true);
    };
    const onStaleStream = () => {
      void fetchMarkers(true, true);
    };
    window.addEventListener('neptun:markers-sync', onVersionSync);
    window.addEventListener('neptun:markers-force-reconcile', onStaleStream);
    return () => {
      window.removeEventListener('neptun:markers-sync', onVersionSync);
      window.removeEventListener('neptun:markers-force-reconcile', onStaleStream);
    };
  }, [fetchMarkers]);

  // SSE reconnect / new socket → full snapshot (fixes stale map after long idle or silent drops).
  // `online` → recover after flaky mobile networks without waiting for SSE error backoff.
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const reconcile = () => {
      void fetchMarkers(true, true);
    };
    const onSseOpen = () => reconcile();
    const onOnline = () => reconcile();
    window.addEventListener('neptun:sse-open', onSseOpen);
    window.addEventListener('online', onOnline);
    return () => {
      window.removeEventListener('neptun:sse-open', onSseOpen);
      window.removeEventListener('online', onOnline);
    };
  }, [fetchMarkers]);

  const upsertMarkerFromSse = useCallback((markerData: Record<string, unknown>): boolean => {
    const lat = Number(markerData.lat);
    const lng = Number(markerData.lng);
    const id = typeof markerData.id === 'string' ? markerData.id : '';
    if (!id || !Number.isFinite(lat) || !Number.isFinite(lng)) return false;

    const newMarker: Marker = {
      id,
      track_id: typeof markerData.track_id === 'string' ? markerData.track_id : undefined,
      lat,
      lng,
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
      positions: Array.isArray(markerData.positions)
        ? normalizeTrackPoints(markerData.positions as Array<Record<string, unknown>>)
        : [{
            lat,
            lng,
            ts: normalizeEpochMs(markerData.created_at_epoch),
            source: (markerData.channel_name as string) || 'sse',
          }],
      placement_mode: typeof markerData.placement_mode === 'string' ? markerData.placement_mode : undefined,
      resolve_status: typeof markerData.resolve_status === 'string' ? markerData.resolve_status : undefined,
      geocode_tier: typeof markerData.geocode_tier === 'string' ? markerData.geocode_tier : undefined,
      geo_decision_reason: typeof markerData.geo_decision_reason === 'string' ? markerData.geo_decision_reason : undefined,
      geocode_source: typeof markerData.geocode_source === 'string' ? markerData.geocode_source : undefined,
      candidates_count: typeof markerData.candidates_count === 'number' ? markerData.candidates_count : undefined,
      publication_class: markerData.publication_class as Marker['publication_class'],
      publication_score: typeof markerData.publication_score === 'number' ? markerData.publication_score : undefined,
      publication_reasons: Array.isArray(markerData.publication_reasons)
        ? markerData.publication_reasons as string[]
        : undefined,
      event_fingerprint: typeof markerData.event_fingerprint === 'string' ? markerData.event_fingerprint : undefined,
      manual: markerData.manual === true,
      confidence: typeof markerData.confidence === 'number' ? markerData.confidence : undefined,
      confidence_0_100: typeof markerData.confidence_0_100 === 'number' ? markerData.confidence_0_100 : undefined,
      observations: Array.isArray(markerData.observations)
        ? normalizeTrackPoints(markerData.observations as Array<Record<string, unknown>>)
        : undefined,
    };
    applyTrackLifecycleFromPayload(newMarker, markerData);
    applyDisplayPolicyFromSsePayload(newMarker, markerData);

    setMarkers((prev) => {
      const idx = prev.findIndex((m) => String(m.id) === id);
      if (idx === -1) return [...prev, newMarker];
      const next = [...prev];
      next[idx] = { ...next[idx], ...newMarker };
      return next;
    });
    return true;
  }, []);

  // SSE push — apply marker payload immediately, then use a short debounced
  // snapshot fetch only for consistency / batch events.
  const sseTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useMarkerSSE(useCallback((data: Record<string, unknown>) => {
    // After admin delete, marker_delete already removed locally; refetch can resurrect
    // stale rows from another PM2 worker before destroyed_tracks propagates.
    if (data?.reason === 'admin_delete') {
      if (sseTimerRef.current) {
        clearTimeout(sseTimerRef.current);
        sseTimerRef.current = null;
      }
      return;
    }
    const appliedDirectly = upsertMarkerFromSse(data);
    if (sseTimerRef.current) clearTimeout(sseTimerRef.current);
    sseTimerRef.current = setTimeout(() => {
      sseTimerRef.current = null;
      fetchMarkers(appliedDirectly);
    }, SSE_FETCH_DEBOUNCE);
  }, [fetchMarkers, upsertMarkerFromSse]));

  // Marker delete SSE — remove immediately (no refetch, avoids stale data from other PM2 workers)
  useMarkerDeleteSSE(useCallback((deletedId: string) => {
    setMarkers((prev) => prev.filter((m) => m.id !== deletedId && m.track_id !== deletedId));
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
        if (typeof markerData.placement_mode === 'string') {
          existing.placement_mode = markerData.placement_mode;
        }
        if (typeof markerData.resolve_status === 'string') {
          existing.resolve_status = markerData.resolve_status;
        }
        if (typeof markerData.geocode_tier === 'string') {
          existing.geocode_tier = markerData.geocode_tier;
        }
        if (typeof markerData.geo_decision_reason === 'string') {
          existing.geo_decision_reason = markerData.geo_decision_reason;
        }
        if (typeof markerData.geocode_source === 'string') {
          existing.geocode_source = markerData.geocode_source;
        }
        if (typeof markerData.candidates_count === 'number') {
          existing.candidates_count = markerData.candidates_count;
        }
        if (typeof markerData.publication_class === 'string') {
          existing.publication_class = markerData.publication_class as Marker['publication_class'];
        }
        if (typeof markerData.publication_score === 'number') {
          existing.publication_score = markerData.publication_score;
        }
        if (Array.isArray(markerData.publication_reasons)) {
          existing.publication_reasons = markerData.publication_reasons as string[];
        }
        if (typeof markerData.event_fingerprint === 'string') {
          existing.event_fingerprint = markerData.event_fingerprint;
        }
        if (markerData.manual === true) existing.manual = true;
        if (markerData.manual === false) existing.manual = false;
        if (typeof markerData.confidence === 'number') existing.confidence = markerData.confidence;
        if (typeof markerData.confidence_0_100 === 'number') {
          existing.confidence_0_100 = markerData.confidence_0_100;
        }
        if (Array.isArray(markerData.observations)) {
          existing.observations = normalizeTrackPoints(markerData.observations as Array<Record<string, unknown>>);
        }
        applyTrackLifecycleFromPayload(existing, markerData);

        const positions: TrackPosition[] = existing.positions ? [...existing.positions] : [];
        if (latN != null && lngN != null) {
          const tsRaw = toNum(markerData.ts) ?? toNum(markerData.created_at_epoch) ?? Date.now();
          positions.push({
            lat: latN,
            lng: lngN,
            ts: normalizeEpochMs(tsRaw),
            source: (markerData.channel_name as string) || 'sse',
          });
          // Keep max 50 locally too
          if (positions.length > 50) positions.splice(0, positions.length - 50);
        }
        existing.positions = positions;

        existing.date = new Date().toISOString();
        applyDisplayPolicyFromSsePayload(existing, markerData);
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
              ts: normalizeEpochMs(p.ts),
              source: (p.source as string) || 'unknown',
            }))
          : [{
              lat: markerData.lat as number,
              lng: markerData.lng as number,
              ts: normalizeEpochMs(markerData.created_at_epoch),
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
          placement_mode: typeof markerData.placement_mode === 'string' ? markerData.placement_mode : undefined,
          resolve_status: typeof markerData.resolve_status === 'string' ? markerData.resolve_status : undefined,
          geocode_tier: typeof markerData.geocode_tier === 'string' ? markerData.geocode_tier : undefined,
          geo_decision_reason: typeof markerData.geo_decision_reason === 'string' ? markerData.geo_decision_reason : undefined,
          geocode_source: typeof markerData.geocode_source === 'string' ? markerData.geocode_source : undefined,
          candidates_count: typeof markerData.candidates_count === 'number' ? markerData.candidates_count : undefined,
          manual: markerData.manual === true,
          confidence: typeof markerData.confidence === 'number' ? markerData.confidence : undefined,
          confidence_0_100: typeof markerData.confidence_0_100 === 'number' ? markerData.confidence_0_100 : undefined,
          observations: Array.isArray(markerData.observations)
            ? normalizeTrackPoints(markerData.observations as Array<Record<string, unknown>>)
            : undefined,
        };
        applyTrackLifecycleFromPayload(newMarker, markerData);
        const created: Marker = { ...newMarker };
        applyDisplayPolicyFromSsePayload(created, markerData);
        return [...prev, created];
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

  // Fallback polling: active backup for SSE gaps, 5min hidden.
  usePolling(
    useCallback(() => {
      void fetchMarkers(false, true);
    }, [fetchMarkers]),
    FALLBACK_POLLING_INTERVAL,
    HIDDEN_POLLING_INTERVAL_DESKTOP,
  );

  // Strict Mode remount can strand inFlight=true while the abandoned fetch never resolves —
  // same pattern as useAlarms.
  useEffect(
    () => () => {
      inFlightRef.current = false;
    },
    [],
  );

  // Force refresh — clears ETag, waits for nginx cache to expire, then fetches
  const forceRefreshMarkers = useCallback(async () => {
    etagRef.current = null;
    // Wait for nginx API_CACHE to expire (3s cache + margin)
    await new Promise((r) => setTimeout(r, 3500));
    inFlightRef.current = false; // ensure not blocked
    await fetchMarkers(true, true);
  }, [fetchMarkers]);

  return { markers, ballisticThreat, fetchMarkers, forceRefreshMarkers, serverTimeOffset };
}
