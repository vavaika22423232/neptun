/**
 * Build filtered Marker[] from in-memory markers store.
 * Used by /api/data and /api/threats so both always see the same data.
 */
import type { Marker } from '@/types';
import { loadSettings, loadHidden } from '@/lib/admin/data';
import { getRawMessages } from '@/lib/markers-store';
import {
  computeMarkerDisplayPolicy,
  mergeMarkerDisplayPolicyConfig,
  type CorroborationContext,
} from '@/lib/marker-display-policy';
import {
  markerPassesPublicMapRawFilter,
  parseRawMarkerMessageTimeMs,
  type PublicMapRawFilterContext,
} from '@/lib/marker-publication';
import { isLatLngInOblastHasc } from '@/lib/ukraine-oblast-validate';
import { mapStoreRecordToMarker } from '@/lib/map-store-record-to-marker';

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
  const ttlEnabled = settings.ttlEnabled;
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
  const filterCtx: Omit<PublicMapRawFilterContext, 'messageTimeMs'> = {
    minConf,
    dualSourceMapGate: settings.dualSourceMapGate === true,
    ttlEnabled,
    cutoffMs,
    hiddenSet,
  };

  const mapped: Marker[] = messages
    .filter((m: Record<string, unknown>) => {
      const messageTimeMs = parseRawMarkerMessageTimeMs(m);
      return markerPassesPublicMapRawFilter(m, { ...filterCtx, messageTimeMs });
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
