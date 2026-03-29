/**
 * Build filtered Marker[] from in-memory markers store.
 * Used by /api/data and /api/threats so both always see the same data.
 */
import type { Marker, Trajectory } from '@/types';
import { isPlausibleThreatCoordinate } from '@/lib/geo-bounds';
import { loadSettings, loadHidden } from '@/lib/admin/data';
import { getRawMessages } from '@/lib/markers-store';
import {
  maxSpeedKmhForThreatType,
  sanitizeTrackPoints,
  sanitizeTrajectoryEndpoints,
  sanitizeTrajectoryWaypoints,
} from '@/lib/track-sanitize';

function parseMessageTime(m: Record<string, unknown>): number {
  if (m.track_id && typeof m.last_update_epoch === 'number' && m.last_update_epoch > 1000000000) {
    const t = m.last_update_epoch as number;
    return t > 10000000000 ? t : t * 1000;
  }
  const createdEpoch = m.created_at_epoch;
  if (typeof createdEpoch === 'number' && createdEpoch > 1000000000) {
    return createdEpoch > 10000000000 ? createdEpoch : createdEpoch * 1000;
  }
  const ts = (m.ts || m.timestamp || m.date || '') as string;
  if (ts) {
    const normalized = ts.includes('T') ? ts : ts.replace(' ', 'T');
    const parsed = new Date(normalized).getTime();
    if (!isNaN(parsed) && parsed > 0) return parsed;
  }
  const unix = m.unix_ts || m.created_at;
  if (typeof unix === 'number' && unix > 1000000000) {
    return unix > 10000000000 ? unix : unix * 1000;
  }
  return -1;
}

function clampOptionalSpeed(kmh: number | undefined, cap: number): number | undefined {
  if (typeof kmh !== 'number' || !Number.isFinite(kmh) || kmh <= 0) return undefined;
  return Math.min(kmh, cap);
}

/** Align track point epochs to ms for the map (same rule as markers-store). */
function normalizeTrackPointTs(ts: number): number {
  if (!Number.isFinite(ts) || ts <= 0) return Date.now();
  return ts > 10_000_000_000 ? Math.round(ts) : Math.round(ts * 1000);
}

function markerActivityMs(m: Marker): number {
  if (typeof m.last_update_epoch === 'number' && m.last_update_epoch > 1_000_000_000) {
    const e = m.last_update_epoch;
    return e > 10_000_000_000 ? e : e * 1000;
  }
  if (typeof m.created_at_epoch === 'number' && m.created_at_epoch > 1_000_000_000) {
    const e = m.created_at_epoch;
    return e > 10_000_000_000 ? e : e * 1000;
  }
  if (m.date) {
    const t = new Date(m.date).getTime();
    if (!isNaN(t)) return t;
  }
  return 0;
}

function dedupeRegistryKey(m: Marker): string {
  const tid = m.track_id != null ? String(m.track_id).trim() : '';
  if (tid.length > 0) return `t:${tid}`;
  const id = m.id != null ? String(m.id).trim() : '';
  if (id.length > 0) return `i:${id}`;
  return `s:${m.lat.toFixed(3)}_${m.lng.toFixed(3)}_${m.threat_type || 'x'}`;
}

function mergeRicher(a: Marker, b: Marker): Marker {
  const ka = markerActivityMs(a);
  const kb = markerActivityMs(b);
  if (kb > ka) return b;
  if (ka > kb) return a;
  const pa = a.positions?.length ?? 0;
  const pb = b.positions?.length ?? 0;
  return pb > pa ? b : a;
}

export interface BuildMarkersOptions {
  /** PRO: use 60+ min retention instead of admin default (30) */
  extendedRange?: boolean;
  /** Явний ліміт хвилин історії (60–240). Пріоритет над extendedRange */
  retentionMinutes?: number;
}

export function buildMarkers(options?: BuildMarkersOptions): Marker[] {
  const messages = getRawMessages();

  let monitorMinutes = 30;
  let ttlEnabled = true;
  let minConf = 0.3;
  try {
    const settings = loadSettings();
    monitorMinutes = settings.monitorPeriod || 30;
    ttlEnabled = settings.ttlEnabled;
    minConf = settings.minConfidence ?? 0.3;
  } catch { /* use defaults */ }

  if (options?.retentionMinutes != null) {
    monitorMinutes = Math.max(monitorMinutes, Math.min(240, options.retentionMinutes));
  } else if (options?.extendedRange) {
    monitorMinutes = Math.max(monitorMinutes, 60);
  }

  let hiddenSet: Set<string> = new Set();
  try {
    const hiddenList = loadHidden();
    hiddenSet = new Set(hiddenList);
  } catch { /* empty set */ }

  const cutoffMs = ttlEnabled ? Date.now() - monitorMinutes * 60 * 1000 : 0;

  const mapped: Marker[] = messages
    .filter((m: Record<string, unknown>) => {
      const lat = Number(m.lat);
      const lng = Number(m.lng);
      if (!Number.isFinite(lat) || !Number.isFinite(lng)) return false;
      if (!isPlausibleThreatCoordinate(lat, lng, { allowOutsideThreatRegion: Boolean(m.manual) })) {
        return false;
      }
      if (m.manual) return true;
      if (ttlEnabled && cutoffMs > 0) {
        const msgTime = parseMessageTime(m);
        if (msgTime < 0) return false;
        if (msgTime > 0 && msgTime < cutoffMs) return false;
      }
      const hiddenKey = `${m.lat},${m.lng}|${m.text || ''}|${m.manual ? 'manual' : 'auto'}`;
      if (hiddenSet.has(hiddenKey)) return false;
      if (m.hidden === true) return false;
      if (typeof (m.confidence as number) === 'number' && (m.confidence as number) < minConf) return false;
      return true;
    })
    .map((m: Record<string, unknown>) => {
      const lat = Number(m.lat);
      const lng = Number(m.lng);
      const lastEp = m.last_update_epoch as number | undefined;
      const createdEp = m.created_at_epoch as number | undefined;
      const flightPhase = m.flight_phase as Marker['flight_phase'] | undefined;
      const tt = (m.threat_type || m.type || 'default') as string;
      const speedCap = maxSpeedKmhForThreatType(tt);
      const sk = clampOptionalSpeed(m.speed_kmh as number | undefined, speedCap);
      const csk = clampOptionalSpeed(m.computed_speed_kmh as number | undefined, speedCap);
      const rawTraj = m.trajectory as Record<string, unknown> | undefined;
      let trajectoryOut: Marker['trajectory'] = null;
      if (rawTraj) {
        const ends = sanitizeTrajectoryEndpoints(
          rawTraj.start as [number, number] | undefined,
          rawTraj.end as [number, number] | undefined,
          tt,
        );
        const wpts = sanitizeTrajectoryWaypoints(
          rawTraj.waypoints as [number, number][] | undefined,
          tt,
        );
        trajectoryOut = {
          start: ends.start,
          end: ends.end,
          predicted: rawTraj.predicted as boolean | undefined,
          source: rawTraj.source as Trajectory['source'],
          prediction_confidence: rawTraj.prediction_confidence as number | undefined,
          waypoints: wpts,
          flight_phase: rawTraj.flight_phase as Trajectory['flight_phase'],
        };
        const hasGeom =
          trajectoryOut.start ||
          trajectoryOut.end ||
          (trajectoryOut.waypoints && trajectoryOut.waypoints.length > 0);
        const hasMeta =
          trajectoryOut.predicted != null ||
          trajectoryOut.source != null ||
          trajectoryOut.prediction_confidence != null ||
          trajectoryOut.flight_phase != null;
        if (!hasGeom && !hasMeta) trajectoryOut = null;
      }
      return {
        id: m.id as string,
        track_id: (m.track_id || undefined) as string | undefined,
        lat,
        lng,
        threat_type: tt,
        place: (m.place || m.city || m.location || '') as string,
        region: (m.region || '') as string,
        text: (m.text || '') as string,
        date: (m.date || m.timestamp || m.ts || '') as string,
        count: (m.count || 1) as number,
        marker_icon: (m.marker_icon || '') as string,
        course_bearing: (m.course_bearing as number) || null,
        course_direction: (m.course_direction || '') as string,
        distance_km: (m.distance_km as number) || undefined,
        speed_kmh: sk,
        computed_speed_kmh: csk,
        confidence: (m.confidence as number) || undefined,
        resolve_status: (m.resolve_status || '') as string,
        trajectory: trajectoryOut,
        trajectory_source: (m.trajectory_source || '') as string,
        prediction_confidence: (m.prediction_confidence as number) || undefined,
        created_at_epoch: createdEp || undefined,
        last_update_epoch: lastEp || undefined,
        origin: (m.origin || '') as string,
        flight_phase: flightPhase,
        ticker_bearing: (m.ticker_bearing as number) ?? null,
        is_estimated: Boolean(m.is_estimated),
        positions: Array.isArray(m.positions)
          ? sanitizeTrackPoints(
              (m.positions as Array<Record<string, unknown>>).slice(-24).map((p) => ({
                lat: Number(p.lat),
                lng: Number(p.lng),
                ts: normalizeTrackPointTs(Number(p.ts)),
                source: (p.source || '') as string,
              })),
              speedCap,
            ).slice(-20)
          : undefined,
        observations: Array.isArray(m.observations)
          ? sanitizeTrackPoints(
              (m.observations as Array<Record<string, unknown>>).slice(-24).map((p) => ({
                lat: Number(p.lat),
                lng: Number(p.lng),
                ts: normalizeTrackPointTs(Number(p.ts)),
                source: (p.source || '') as string,
              })),
              speedCap,
            ).slice(-20)
          : undefined,
        observation_count: (m.observation_count as number) || undefined,
      } as Marker;
    });

  const byKey = new Map<string, Marker>();
  for (const marker of mapped) {
    const key = dedupeRegistryKey(marker);
    const existing = byKey.get(key);
    byKey.set(key, existing ? mergeRicher(existing, marker) : marker);
  }

  return Array.from(byKey.values()).sort((a, b) => markerActivityMs(b) - markerActivityMs(a));
}
