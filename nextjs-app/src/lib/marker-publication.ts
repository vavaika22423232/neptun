/**
 * Single place for “should this raw store row appear on the public map?” vs “should ingest broadcast it?”.
 * Keeps SSE / build-markers / confidence math aligned.
 */
import { loadSettings } from '@/lib/admin/data';
import { recordHasPhantomAvia } from '@/lib/corroboration-public-gate';
import { isPlausibleThreatCoordinate } from '@/lib/geo-bounds';

/** Confidence used for thresholding when field missing (not 100%). */
export function effectiveMarkerConfidence(marker: Record<string, unknown>, minConf: number): number {
  if (typeof marker.confidence === 'number' && Number.isFinite(marker.confidence)) {
    return Math.min(1, Math.max(0, marker.confidence));
  }
  const c100 = marker.confidence_0_100;
  if (typeof c100 === 'number' && Number.isFinite(c100)) {
    return Math.min(1, Math.max(0, c100 / 100));
  }
  return minConf;
}

/** @deprecated use effectiveMarkerConfidence */
export const effectiveIngestConfidence = effectiveMarkerConfidence;

export function markerBlockedByPlacementMode(marker: Record<string, unknown>): boolean {
  const pm = typeof marker.placement_mode === 'string' ? marker.placement_mode : '';
  return (
    pm === 'multi_reference_suppressed' ||
    pm === 'sea_context_mismatch' ||
    pm === 'low_map_confidence'
  );
}

export function markerBlockedByTrackState(marker: Record<string, unknown>): boolean {
  if (Boolean(marker.manual)) return false;
  const state = marker.track_state;
  if (state === 'lost' || state === 'stale' || state === 'split_candidate') return true;

  const trackConfidence = marker.track_confidence;
  if (typeof trackConfidence === 'number' && Number.isFinite(trackConfidence)) {
    return trackConfidence < 0.5;
  }

  return false;
}

export function markerBlockedByDualSourcePending(
  marker: Record<string, unknown>,
  dualSourceMapGate: boolean,
): boolean {
  const phantomAvia = recordHasPhantomAvia(marker);
  return (
    (dualSourceMapGate === true || phantomAvia) && marker.corroboration_pending === true
  );
}

/**
 * Public map: `hidden === true` is allowed only for stale dual-only rows (legacy / transition).
 * Ingest broadcast: never broadcast hidden markers (stricter).
 */
export function markerExcludedByHiddenForPublicMap(
  marker: Record<string, unknown>,
  dualSourceMapGate: boolean,
): boolean {
  if (marker.hidden !== true) return false;
  const phantomAvia = recordHasPhantomAvia(marker);
  const staleDualOnly =
    !dualSourceMapGate && !phantomAvia && marker.corroboration_pending === true;
  return !staleDualOnly;
}

export function ingestShouldBroadcastMarker(
  marker: Record<string, unknown>,
  minConf: number,
): boolean {
  if (Boolean(marker.manual)) return true;
  const s = loadSettings();
  if (markerBlockedByDualSourcePending(marker, s.dualSourceMapGate === true)) return false;
  if (marker.hidden === true) return false;
  if (markerBlockedByTrackState(marker)) return false;
  if (markerBlockedByPlacementMode(marker)) return false;
  return effectiveMarkerConfidence(marker, minConf) >= minConf;
}

export type PublicMapRawFilterContext = {
  minConf: number;
  dualSourceMapGate: boolean;
  ttlEnabled: boolean;
  cutoffMs: number;
  hiddenSet: Set<string>;
  /** Precomputed message time (ms) from {@link parseRawMarkerMessageTimeMs}; -1 if unknown */
  messageTimeMs: number;
};

/** Observation / message time for TTL (same semantics as build-markers). */
export function parseRawMarkerMessageTimeMs(m: Record<string, unknown>): number {
  const obs = m.observations as Array<{ ts?: number }> | undefined;
  if (obs && obs.length > 0) {
    for (let i = obs.length - 1; i >= 0; i--) {
      const t = obs[i]?.ts;
      if (typeof t !== 'number' || !Number.isFinite(t) || t <= 0) continue;
      return t > 10_000_000_000 ? t : Math.round(t * 1000);
    }
  }

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

/**
 * Whether a raw markers-store row should pass into the public map pipeline (before dedupe / display policy).
 */
export function markerPassesPublicMapRawFilter(
  m: Record<string, unknown>,
  ctx: PublicMapRawFilterContext,
): boolean {
  const lat = Number(m.lat);
  const lng = Number(m.lng);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return false;
  if (!isPlausibleThreatCoordinate(lat, lng, { allowOutsideThreatRegion: Boolean(m.manual) })) {
    return false;
  }
  if (m.manual) return true;

  if (ctx.ttlEnabled && ctx.cutoffMs > 0) {
    const msgTime = ctx.messageTimeMs;
    if (msgTime < 0) return false;
    if (msgTime > 0 && msgTime < ctx.cutoffMs) return false;
  }

  const hiddenKey = `${m.lat},${m.lng}|${m.text || ''}|${m.manual ? 'manual' : 'auto'}`;
  if (ctx.hiddenSet.has(hiddenKey)) return false;

  if (markerBlockedByDualSourcePending(m, ctx.dualSourceMapGate)) return false;

  if (markerExcludedByHiddenForPublicMap(m, ctx.dualSourceMapGate)) return false;

  if (markerBlockedByTrackState(m)) return false;

  if (markerBlockedByPlacementMode(m)) return false;

  if (effectiveMarkerConfidence(m, ctx.minConf) < ctx.minConf) return false;
  return true;
}
