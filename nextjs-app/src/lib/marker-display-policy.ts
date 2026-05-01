/**
 * Public-map policy: what we imply about position accuracy.
 * Icons stay per threat_type; display_class drives uncertainty geometry + copy on the client.
 * Safe to import from client bundles (no Node/fs dependencies).
 */
import type { Marker, MarkerDisplayClass } from '@/types';
import { resolveThreatBearingDeg } from '@/lib/threat-bearing';

export type { MarkerDisplayClass };

export type MarkerDisplayFields = {
  display_class: MarkerDisplayClass;
  show_precise_pin: boolean;
  display_uncertainty_km: number;
  display_trust_hint_uk: string;
};

/** K/T/R and ring radii — merge with admin settings on the server, use defaults on the client. */
export interface MarkerDisplayPolicyConfig {
  corroborationMinObservations: number;
  corroborationWindowMinutes: number;
  corroborationMaxRadiusKm: number;
  /** Мінімум унікальних `source` серед recent точок (0 = вимкнено; 2 = проксі «два канали»). */
  corroborationMinDistinctSources: number;
  regionUncertaintyKm: number;
  corroboratedUncertaintyKm: number;
}

/** Опційний серверний контекст (не імпортує geojson у клієнт). */
export type CorroborationContext = {
  pointInStatedOblast?: (lat: number, lng: number, hascUpper: string) => boolean;
};

export const DEFAULT_MARKER_DISPLAY_POLICY: MarkerDisplayPolicyConfig = {
  corroborationMinObservations: 2,
  corroborationWindowMinutes: 30,
  corroborationMaxRadiusKm: 45,
  corroborationMinDistinctSources: 2,
  regionUncertaintyKm: 38,
  corroboratedUncertaintyKm: 9,
};

export function mergeMarkerDisplayPolicyConfig(
  partial?: Partial<MarkerDisplayPolicyConfig> | null,
): MarkerDisplayPolicyConfig {
  return { ...DEFAULT_MARKER_DISPLAY_POLICY, ...partial };
}

function policyNums(config: MarkerDisplayPolicyConfig) {
  return {
    K: config.corroborationMinObservations,
    T: config.corroborationWindowMinutes,
    R: config.corroborationMaxRadiusKm,
    regionKm: config.regionUncertaintyKm,
    pointKm: config.corroboratedUncertaintyKm,
  };
}

function haversineKm(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLng = ((lng2 - lng1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLng / 2) *
      Math.sin(dLng / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

function pointTsMs(ts: number): number {
  if (!Number.isFinite(ts) || ts <= 0) return 0;
  return ts > 10_000_000_000 ? Math.round(ts) : Math.round(ts * 1000);
}

/** K observations within T minutes, pairwise spread <= R km (cluster on recent points). */
export function meetsCorroborationCluster(
  marker: Marker,
  config: MarkerDisplayPolicyConfig,
  ctx?: CorroborationContext,
): boolean {
  const { K, T, R } = policyNums(config);
  const pts = marker.observations?.length ? marker.observations : marker.positions ?? [];
  if (pts.length < K) return false;
  const cutoff = Date.now() - T * 60_000;
  const recent = pts.filter((p) => pointTsMs(p.ts) >= cutoff);
  if (recent.length < K) return false;
  let maxD = 0;
  for (let i = 0; i < recent.length; i++) {
    for (let j = i + 1; j < recent.length; j++) {
      maxD = Math.max(
        maxD,
        haversineKm(recent[i].lat, recent[i].lng, recent[j].lat, recent[j].lng),
      );
    }
  }
  if (maxD > R) return false;

  const minSrc = config.corroborationMinDistinctSources ?? 0;
  if (minSrc >= 2) {
    const sources = new Set(
      recent.map((p) => {
        const s = (p.source || '').trim();
        return s.length > 0 ? s : '_unknown';
      }),
    );
    if (sources.size < minSrc) return false;
  }

  const hascRaw = marker.resolved_oblast_hasc?.trim();
  if (hascRaw && ctx?.pointInStatedOblast) {
    const h = hascRaw.toUpperCase();
    for (const p of recent) {
      if (!ctx.pointInStatedOblast(p.lat, p.lng, h)) return false;
    }
  }

  return true;
}

function isRegionMismatch(marker: Marker): boolean {
  const rs = (marker.resolve_status || '').toLowerCase();
  return rs.includes('mismatch') || rs.includes('region_mismatch');
}

/**
 * Resolver / legacy rows may have maritime or offshore-style `resolve_status` (e.g. water targets).
 * Those coords can be in water; never imply a land pin.
 * Mirrors keywords in `feed-maritime-normalize.ts` (`offshore` / maritime context).
 * @param marker — current marker
 * @returns true when public map must not show a precise placement for this status
 */
export function isOffshoreOrMaritimeResolve(marker: Marker): boolean {
  const rs = (marker.resolve_status || '').toLowerCase().trim();
  if (!rs) return false;
  return /offshore|акватор|морськ|морська|морськ\w*|maritime|прибережн/.test(rs);
}

function candidateCount(marker: Marker): number {
  if (typeof marker.candidates_count === 'number' && Number.isFinite(marker.candidates_count)) {
    return Math.max(0, marker.candidates_count);
  }
  const c = marker.candidates;
  if (Array.isArray(c)) return c.length;
  return 0;
}

function isMultiGeocode(marker: Marker): boolean {
  const tier = (marker.geocode_tier || '').toLowerCase();
  if (tier === 'multi' || tier === 'ambiguous') return true;
  return candidateCount(marker) > 1;
}

function hasCorridorGeometry(marker: Marker): boolean {
  const t = marker.trajectory;
  if (t?.start && t?.end) return true;
  if (t?.waypoints && t.waypoints.length >= 2) return true;
  return resolveThreatBearingDeg(marker) != null;
}

/**
 * Compute display policy for one marker (already normalized in build-markers).
 */
export function computeMarkerDisplayPolicy(
  marker: Marker,
  config: MarkerDisplayPolicyConfig,
  ctx?: CorroborationContext,
): MarkerDisplayFields {
  const { regionKm, pointKm } = policyNums(config);
  const manual = Boolean(marker.manual);
  const pm = (marker.placement_mode || '').toLowerCase();
  const corroborated = meetsCorroborationCluster(marker, config, ctx);
  const multiGeo = isMultiGeocode(marker);

  if (manual) {
    return {
      display_class: 'manual_override',
      show_precise_pin: true,
      display_uncertainty_km: Math.min(pointKm, 5),
      display_trust_hint_uk: 'Позиція з ручним підтвердженням.',
    };
  }

  if (isOffshoreOrMaritimeResolve(marker)) {
    return {
      display_class: 'region_signal',
      show_precise_pin: false,
      display_uncertainty_km: Math.max(regionKm, 48),
      display_trust_hint_uk:
        'Оцінна позиція в акваторії чи на підході; пін — орієнтир, а не гарантовано над зазначеним НП у тексті.',
    };
  }

  if (pm === 'predictive' && hasCorridorGeometry(marker)) {
    return {
      display_class: 'corridor_or_bearing',
      show_precise_pin: false,
      display_uncertainty_km: regionKm,
      display_trust_hint_uk: 'Ймовірний напрямок / коридор (орієнтовно).',
    };
  }

  if (pm === 'predictive') {
    return {
      display_class: 'region_signal',
      show_precise_pin: false,
      display_uncertainty_km: regionKm,
      display_trust_hint_uk: 'Орієнтовно в межах регіону; точна позиція не стверджується.',
    };
  }

  if (pm === 'approximate' || isRegionMismatch(marker)) {
    return {
      display_class: 'region_signal',
      show_precise_pin: false,
      display_uncertainty_km: regionKm,
      display_trust_hint_uk: 'Орієнтовно в межах регіону; точна позиція не стверджується.',
    };
  }

  if (multiGeo && !corroborated) {
    return {
      display_class: 'region_signal',
      show_precise_pin: false,
      display_uncertainty_km: regionKm,
      display_trust_hint_uk: 'Кілька варіантів геокоду; показ орієнтовний.',
    };
  }

  if (corroborated) {
    return {
      display_class: 'corroborated_point',
      show_precise_pin: true,
      display_uncertainty_km: pointKm,
      display_trust_hint_uk: 'За кількома спостереженнями в узгодженому районі.',
    };
  }

  return {
    display_class: 'region_signal',
    show_precise_pin: false,
    display_uncertainty_km: regionKm,
    display_trust_hint_uk: 'Орієнтовно в межах регіону; точна позиція не стверджується.',
  };
}
