/**
 * Build filtered Marker[] from in-memory markers store.
 * Used by /api/data and /api/threats so both always see the same data.
 */
import type { Marker } from '@/types';
import { isPlausibleThreatCoordinate } from '@/lib/geo-bounds';
import { loadSettings, loadHidden } from '@/lib/admin/data';
import { getRawMessages } from '@/lib/markers-store';
import {
  computeMarkerDisplayPolicy,
  mergeMarkerDisplayPolicyConfig,
  type CorroborationContext,
} from '@/lib/marker-display-policy';
import { isLatLngInOblastHasc } from '@/lib/ukraine-oblast-validate';
import { mapStoreRecordToMarker } from '@/lib/map-store-record-to-marker';
import { recordHasPhantomAvia } from '@/lib/corroboration-public-gate';

/** Last *reported* observation time (ms). Ticker-only `positions` updates do not refresh this. */
function lastObservationTimeMs(m: Record<string, unknown>): number {
  const obs = m.observations as Array<{ ts?: number }> | undefined;
  if (!obs || obs.length === 0) return -1;
  for (let i = obs.length - 1; i >= 0; i--) {
    const t = obs[i]?.ts;
    if (typeof t !== 'number' || !Number.isFinite(t) || t <= 0) continue;
    return t > 10_000_000_000 ? t : Math.round(t * 1000);
  }
  return -1;
}

function parseMessageTime(m: Record<string, unknown>): number {
  const obsMs = lastObservationTimeMs(m);
  if (obsMs > 0) return obsMs;

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
  /** When true and `retentionMinutes` omitted: `monitorMinutes = max(admin, 60)`. */
  extendedRange?: boolean;
  /** Явний ліміт хвилин історії (до 240). Пріоритет над extendedRange */
  retentionMinutes?: number;
}

/**
 * Build options for HTTP APIs: retention follows admin `monitorPeriod` (not a fixed 3h window).
 * `extendedRange` mirrors `/api/data?timeRange>=60` (public map).
 */
export function buildMarkerOptionsForApi(extendedRange: boolean): BuildMarkersOptions {
  const mp = Math.min(240, loadSettings().monitorPeriod || 30);
  if (extendedRange) {
    return { extendedRange: true, retentionMinutes: mp };
  }
  return {};
}

export function buildMarkers(options?: BuildMarkersOptions): Marker[] {
  const messages = getRawMessages();
  const settings = loadSettings();
  const displayPolicyConfig = mergeMarkerDisplayPolicyConfig({
    corroborationMinObservations: settings.corroborationMinObservations,
    corroborationWindowMinutes: settings.corroborationWindowMinutes,
    corroborationMaxRadiusKm: settings.corroborationMaxRadiusKm,
    corroborationMinDistinctSources: settings.corroborationMinDistinctSources,
    regionUncertaintyKm: settings.regionUncertaintyKm,
    corroboratedUncertaintyKm: settings.corroboratedUncertaintyKm,
  });

  const corroborationCtx: CorroborationContext = {
    pointInStatedOblast: (lat, lng, hascUpper) => isLatLngInOblastHasc(hascUpper, lat, lng),
  };

  let monitorMinutes = settings.monitorPeriod || 30;
  let ttlEnabled = settings.ttlEnabled;
  const minConf = settings.minConfidence ?? 0.65;

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
  const dualSourceMapGate = settings.dualSourceMapGate === true;

  const mapped: Marker[] = messages
    .filter((m: Record<string, unknown>) => {
      const phantomAvia = recordHasPhantomAvia(m);
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
      if ((dualSourceMapGate || phantomAvia) && m.corroboration_pending === true) return false;
      if (m.hidden === true) {
        const staleDualOnly =
          !dualSourceMapGate && !phantomAvia && m.corroboration_pending === true;
        if (!staleDualOnly) return false;
      }
      const pm = typeof m.placement_mode === 'string' ? m.placement_mode : '';
      if (
        pm === 'multi_reference_suppressed'
        || pm === 'sea_context_mismatch'
        || pm === 'low_map_confidence'
      ) {
        return false;
      }
      const c100 = m.confidence_0_100;
      const c01 = m.confidence;
      /** Missing confidence is not treated as 100% — use threshold edge so shape comes from display_class. */
      let effConf = minConf;
      if (typeof c100 === 'number' && Number.isFinite(c100)) {
        effConf = Math.min(1, Math.max(0, c100 / 100));
      } else if (typeof c01 === 'number' && Number.isFinite(c01)) {
        effConf = c01;
      }
      if (effConf < minConf) return false;
      return true;
    })
    .map((m: Record<string, unknown>) => mapStoreRecordToMarker(m));

  const byKey = new Map<string, Marker>();
  for (const marker of mapped) {
    const key = dedupeRegistryKey(marker);
    const existing = byKey.get(key);
    byKey.set(key, existing ? mergeRicher(existing, marker) : marker);
  }

  return Array.from(byKey.values())
    .map((m) => {
      const disp = computeMarkerDisplayPolicy(m, displayPolicyConfig, corroborationCtx);
      return { ...m, ...disp };
    })
    .sort((a, b) => markerActivityMs(b) - markerActivityMs(a));
}
