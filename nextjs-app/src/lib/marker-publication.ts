/**
 * Single place for “should this raw store row appear on the public map?” vs “should ingest broadcast it?”.
 * Keeps SSE / build-markers / confidence math aligned.
 */
import type { AdminSettings } from '@/lib/admin/data';
import { loadHidden, loadSettings } from '@/lib/admin/data';
import { isPlausibleThreatCoordinate } from '@/lib/geo-bounds';
import { isAdjacentUaMaritimeThreatGeography, isPublicMapThreatGeography } from '@/lib/public-threat-geo';
import { evaluateMarkerPublication } from '@/lib/public-marker-policy';
import {
  UAV_PUBLICATION_TYPES as _UAV_TYPES,
  NON_PUBLIC_RESOLVE_STATUSES,
  BAD_PLACE_TOKENS,
  recordHasPhantomAvia as _recordHasPhantomAvia,
} from '@/lib/publication-constants';

export { NON_PUBLIC_RESOLVE_STATUSES, BAD_PLACE_TOKENS };

/** @deprecated Import from publication-constants directly to avoid circular deps. */
export const recordHasPhantomAvia = _recordHasPhantomAvia;

/** Confidence used for thresholding when field missing (not 100%). */
export function effectiveMarkerConfidence(marker: Record<string, unknown>, minConf: number): number {
  if (
    typeof marker.target_lifecycle_state === 'string' &&
    marker.target_lifecycle_state.trim() &&
    typeof marker.target_confidence === 'number' &&
    Number.isFinite(marker.target_confidence)
  ) {
    return Math.min(1, Math.max(0, marker.target_confidence));
  }
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

const UAV_PUBLICATION_TYPES = _UAV_TYPES;

export function isUavClassThreatType(threatType: string | undefined): boolean {
  return UAV_PUBLICATION_TYPES.has(String(threatType || '').toLowerCase());
}

/** Effective confidence threshold for publication / SSE (per marker type). */
export function publicationMinConfidence(marker: Record<string, unknown>, settings: AdminSettings): number {
  const base = settings.minConfidence ?? 0.65;
  const uavFloor = settings.minConfidenceUav;
  if (
    typeof uavFloor === 'number' &&
    Number.isFinite(uavFloor) &&
    isUavClassThreatType(marker.threat_type as string | undefined)
  ) {
    return uavFloor;
  }
  return base;
}

export function markerBlockedByPlacementMode(marker: Record<string, unknown>): boolean {
  const pm = typeof marker.placement_mode === 'string' ? marker.placement_mode : '';
  return (
    pm === 'multi_reference_suppressed' ||
    pm === 'sea_context_mismatch' ||
    pm === 'low_map_confidence'
  );
}


function normalizePlaceToken(value: unknown): string {
  return String(value || '')
    .normalize('NFKC')
    .trim()
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s'ʼ-]/gu, '')
    .replace(/\s+/g, ' ');
}

function candidateCount(marker: Record<string, unknown>): number {
  if (typeof marker.candidates_count === 'number' && Number.isFinite(marker.candidates_count)) {
    return Math.max(0, marker.candidates_count);
  }
  return Array.isArray(marker.candidates) ? marker.candidates.length : 0;
}

export function markerHasAmbiguousGeocode(marker: Record<string, unknown>): boolean {
  const tier = normalizePlaceToken(marker.geocode_tier);
  if (tier === 'multi' || tier === 'ambiguous') return true;
  if (candidateCount(marker) > 1) return true;

  const rs = normalizePlaceToken(marker.resolve_status).replace(/\s+/g, '_');
  if (NON_PUBLIC_RESOLVE_STATUSES.has(rs)) return true;
  return rs.includes('ambiguous') || rs.includes('multi');
}

export function markerHasNonPublicPlaceLabel(marker: Record<string, unknown>): boolean {
  const place = normalizePlaceToken(marker.place || marker.city || marker.location);
  if (!place) return false;
  if (BAD_PLACE_TOKENS.has(place)) return true;

  const compact = place.replace(/[\s'ʼ-]+/g, '');
  if (BAD_PLACE_TOKENS.has(compact)) return true;
  return compact.length < 3 && !/^\d+$/.test(compact);
}

export function markerBlockedByPublicPlacementQuality(marker: Record<string, unknown>): boolean {
  const pm = normalizePlaceToken(marker.placement_mode);
  if (pm === 'trajectory_dead_reckoning') return false;
  if (pm === 'approximate') return marker.position_estimated !== true;
  if (pm === 'predictive') return false;
  if (markerHasAmbiguousGeocode(marker)) return true;
  if (markerHasNonPublicPlaceLabel(marker)) return true;
  return false;
}

function markerHasMaritimeEvidence(marker: Record<string, unknown>): boolean {
  const haystack = [
    marker.place,
    marker.city,
    marker.location,
    marker.region,
    marker.resolve_status,
    marker.placement_mode,
    marker.text,
  ].map(normalizePlaceToken).join(' ');
  return /чорн\w*\s+мор|black\s*sea|азов\w*\s+мор|акватор|морськ|maritime|offshore|sea/.test(haystack);
}

/**
 * True when the marker has a non-maritime land place name (Odesa, Kherson, etc.).
 * A real Ukrainian city name is sufficient to establish that the marker is land-based
 * even when its coordinates fall inside the maritime bounding box.
 */
function markerHasLandPlaceEvidence(marker: Record<string, unknown>): boolean {
  const place = normalizePlaceToken(marker.place || marker.city || marker.location);
  if (!place || place.length < 3) return false;
  // Maritime place names are not land evidence
  if (/чорн\w*\s+мор|black\s*sea|азов\w*\s+мор|акватор|морськ|maritime|offshore|^море$|\bачм\b/.test(place)) return false;
  if (BAD_PLACE_TOKENS.has(place)) return false;
  return true;
}

export function markerBlockedByUnevidencedMaritimePoint(marker: Record<string, unknown>): boolean {
  const lat = Number(marker.lat);
  const lng = Number(marker.lng);
  if (!isAdjacentUaMaritimeThreatGeography(lat, lng)) return false;
  // High-latitude points are more likely on land (Mykolaiv ~47°N, etc.)
  if (lat > 46.7) return false;
  // Odesa (~46.48°N) and Kherson (~46.64°N) fall below the lat guard but are land cities.
  // A non-maritime place name is authoritative evidence that the marker is land-based.
  if (markerHasLandPlaceEvidence(marker)) return false;
  return !markerHasMaritimeEvidence(marker);
}

export function markerBlockedByTrackState(marker: Record<string, unknown>): boolean {
  if (Boolean(marker.manual)) return false;
  const state = marker.track_state;
  // «lost» — знімаємо з карти; «split_candidate» — сумнівна геометрія.
  if (state === 'lost' || state === 'split_candidate') return true;
  
  // «stale» / «extrapolated»: даємо більше часу на карті навіть при низькому visualConfidence
  const isPredictive = state === 'stale' || state === 'extrapolated';
  const trackConfidence = marker.track_confidence;
  
  if (typeof trackConfidence === 'number' && Number.isFinite(trackConfidence)) {
    const targetConfidence = typeof marker.target_confidence === 'number' && Number.isFinite(marker.target_confidence)
      ? marker.target_confidence
      : 0;
    if (
      isPredictive &&
      targetConfidence >= 0.88 &&
      isUavClassThreatType(marker.threat_type as string | undefined)
    ) {
      return false;
    }
    // Для екстрапольованих треків поріг нижчий (0.38), щоб не блимало при переході з observed
    const threshold = isPredictive ? 0.38 : 0.5;
    return trackConfidence < threshold;
  }

  return false;
}

export function markerBlockedByDualSourcePending(
  marker: Record<string, unknown>,
  dualSourceMapGate: boolean,
): boolean {
  // If the dual source gate is globally OFF in admin settings, we don't block
  // ordinary markers for being single-source.
  // HOWEVER, phantom avia (synthetic evidence) ALWAYS requires corroboration.
  const phantomAvia = recordHasPhantomAvia(marker);
  if (!phantomAvia && !dualSourceMapGate) return false;

  const confidence = typeof marker.target_confidence === 'number' && Number.isFinite(marker.target_confidence)
    ? marker.target_confidence
    : typeof marker.confidence === 'number'
      ? marker.confidence
      : 0;
  if (confidence >= 0.88 && isUavClassThreatType(marker.threat_type as string)) return false;

  return marker.corroboration_pending === true || !markerHasDualSourceCorroboration(marker);
}

function coerceChannelPriority(value: unknown): number {
  const n = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(n) ? n : 99;
}

/**
 * True when a marker is allowed through the "2 channels" public gate.
 * Priority-1 official observations bypass the gate; all other rows need two distinct sources.
 */
export function markerHasDualSourceCorroboration(marker: Record<string, unknown>): boolean {
  const observations = marker.observations as Array<Record<string, unknown>> | undefined;
  const evidence =
    observations && observations.length > 0
      ? observations
      : [{ source: marker.channel_name, channel_priority: marker.channel_priority }];

  const hasPriority1 = evidence.some((item) => coerceChannelPriority(item.channel_priority) <= 1);
  if (hasPriority1) return true;

  const sources = new Set(
    evidence
      .map((item) => (typeof item.source === 'string' ? item.source.trim() : ''))
      .filter(Boolean),
  );
  return sources.size >= 2;
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
  
  // If dual gate is ON, we definitely exclude markers marked as hidden/pending
  if (dualSourceMapGate) return true;

  const legacyDualOnly = !phantomAvia && marker.corroboration_pending === true;
  return !legacyDualOnly;
}

function normalizeHiddenText(value: unknown): string {
  return String(value || '')
    .replace(/[^a-zA-Zа-яА-ЯіІїЇєЄ0-9]/g, '')
    .toLowerCase()
    .slice(0, 30);
}

function parseHiddenEntry(entry: string): { lat: number; lng: number; text: string; source: string } | null {
  const [coordPart, text = '', source = ''] = String(entry || '').split('|');
  const [latRaw, lngRaw] = coordPart.split(',');
  const lat = Number(latRaw);
  const lng = Number(lngRaw);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
  return { lat, lng, text, source };
}

function markerMatchesHiddenEntry(marker: Record<string, unknown>, entry: string): boolean {
  const parsed = parseHiddenEntry(entry);
  if (!parsed) return false;

  const lat = Number(marker.lat);
  const lng = Number(marker.lng);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return false;

  const source = marker.manual ? 'manual' : 'auto';
  if (parsed.source && parsed.source !== source) return false;

  // Ticker / spatial merge can move a marker slightly between admin click and next snapshot.
  if (Math.abs(lat - parsed.lat) >= 0.05 || Math.abs(lng - parsed.lng) >= 0.05) return false;

  const hiddenText = normalizeHiddenText(parsed.text);
  if (!hiddenText) return true;
  const markerText = normalizeHiddenText(marker.text);
  if (!markerText) return false;
  return markerText.includes(hiddenText) || hiddenText.includes(markerText);
}

export function markerExcludedByHiddenList(
  marker: Record<string, unknown>,
  hiddenSet: Set<string>,
): boolean {
  const exactKey = `${marker.lat},${marker.lng}|${marker.text || ''}|${marker.manual ? 'manual' : 'auto'}`;
  if (hiddenSet.has(exactKey)) return true;
  for (const entry of hiddenSet) {
    if (markerMatchesHiddenEntry(marker, entry)) return true;
  }
  return false;
}

export function ingestShouldBroadcastMarker(marker: Record<string, unknown>): boolean {
  if (Boolean(marker.manual)) return true;
  const lat = Number(marker.lat);
  const lng = Number(marker.lng);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return false;
  if (!isPlausibleThreatCoordinate(lat, lng)) return false;
  if (!isPublicMapThreatGeography(lat, lng)) return false;
  if (markerBlockedByUnevidencedMaritimePoint(marker)) return false;

  const s = loadSettings();
  let hidden = false;
  try {
    hidden = markerExcludedByHiddenList(marker, new Set(loadHidden()));
  } catch { /* hidden list is best-effort */ }
  const decision = evaluateMarkerPublication(marker, { settings: s, hidden });
  if (!decision.public) return false;
  if (markerBlockedByDualSourcePending(marker, s.dualSourceMapGate === true)) return false;
  if (marker.hidden === true) return false;
  if (markerBlockedByTrackState(marker)) return false;
  if (markerBlockedByPlacementMode(marker)) return false;
  if (markerBlockedByPublicPlacementQuality(marker)) return false;
  const thresh = publicationMinConfidence(marker, s);
  return effectiveMarkerConfidence(marker, thresh) >= thresh;
}

export type PublicMapRawFilterContext = {
  settings: AdminSettings;
  ttlEnabled: boolean;
  cutoffMs: number;
  hiddenSet: Set<string>;
  /** Precomputed message time (ms) from {@link parseRawMarkerMessageTimeMs}; -1 if unknown */
  messageTimeMs: number;
};

export type PublicMapRawFilterDecision = {
  passes: boolean;
  reason: string;
  details?: Record<string, unknown>;
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
 * Whether a tracked target record should pass into the public map pipeline (before dedupe / display policy).
 */
export function explainPublicMapRawFilter(
  m: Record<string, unknown>,
  ctx: PublicMapRawFilterContext,
): PublicMapRawFilterDecision {
  const lat = Number(m.lat);
  const lng = Number(m.lng);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
    return { passes: false, reason: 'invalid_coordinates', details: { lat: m.lat, lng: m.lng } };
  }
  if (!isPlausibleThreatCoordinate(lat, lng, { allowOutsideThreatRegion: Boolean(m.manual) })) {
    return { passes: false, reason: 'implausible_coordinates', details: { lat, lng, manual: Boolean(m.manual) } };
  }

  if (markerExcludedByHiddenList(m, ctx.hiddenSet)) {
    return { passes: false, reason: 'hidden_list', details: { hidden_entries: ctx.hiddenSet.size } };
  }

  if (m.manual) return { passes: true, reason: 'manual_public', details: { lat, lng } };

  if (!isPublicMapThreatGeography(lat, lng)) {
    return { passes: false, reason: 'outside_public_threat_geography', details: { lat, lng } };
  }
  if (markerBlockedByUnevidencedMaritimePoint(m)) {
    return {
      passes: false,
      reason: 'unevidenced_maritime_point',
      details: { lat, lng, place: m.place, region: m.region, resolve_status: m.resolve_status },
    };
  }

  if (ctx.ttlEnabled && ctx.cutoffMs > 0) {
    const msgTime = ctx.messageTimeMs;
    if (msgTime < 0) {
      return { passes: false, reason: 'ttl_missing_message_time', details: { cutoff_ms: ctx.cutoffMs } };
    }
    if (msgTime > 0 && msgTime < ctx.cutoffMs) {
      return {
        passes: false,
        reason: 'ttl_expired',
        details: { message_time_ms: msgTime, cutoff_ms: ctx.cutoffMs, age_ms: Date.now() - msgTime },
      };
    }
  }

  const dualGate = ctx.settings.dualSourceMapGate === true;
  if (markerBlockedByDualSourcePending(m, dualGate)) {
    return {
      passes: false,
      reason: 'dual_source_pending',
      details: {
        dual_gate: dualGate,
        corroboration_pending: m.corroboration_pending === true,
        source_count: m.source_count,
        observations: Array.isArray(m.observations) ? m.observations.length : 0,
        target_confidence: m.target_confidence,
        confidence: m.confidence,
      },
    };
  }

  if (markerExcludedByHiddenForPublicMap(m, dualGate)) {
    return { passes: false, reason: 'hidden_marker', details: { hidden: m.hidden, dual_gate: dualGate } };
  }

  if (markerBlockedByTrackState(m)) {
    return {
      passes: false,
      reason: 'track_state_blocked',
      details: {
        track_state: m.track_state,
        track_confidence: m.track_confidence,
        target_confidence: m.target_confidence,
        threat_type: m.threat_type,
      },
    };
  }

  if (markerBlockedByPlacementMode(m)) {
    return {
      passes: false,
      reason: 'placement_mode_blocked',
      details: { placement_mode: m.placement_mode, resolve_status: m.resolve_status },
    };
  }
  if (markerBlockedByPublicPlacementQuality(m)) {
    return {
      passes: false,
      reason: 'public_placement_quality_blocked',
      details: {
        placement_mode: m.placement_mode,
        resolve_status: m.resolve_status,
        geocode_tier: m.geocode_tier,
        candidates_count: candidateCount(m),
        place: m.place || m.city || m.location,
      },
    };
  }

  const decision = evaluateMarkerPublication(m, { settings: ctx.settings, hidden: false });
  if (!decision.public) {
    return {
      passes: false,
      reason: 'publication_not_public',
      details: {
        class: decision.classification,
        score: decision.score,
        reasons: decision.reasons,
        invariant_violations: decision.invariantViolations,
      },
    };
  }

  const thresh = publicationMinConfidence(m, ctx.settings);
  const confidence = effectiveMarkerConfidence(m, thresh);
  if (confidence < thresh) {
    return {
      passes: false,
      reason: 'confidence_below_threshold',
      details: { confidence, threshold: thresh, target_confidence: m.target_confidence, raw_confidence: m.confidence },
    };
  }
  return {
    passes: true,
    reason: 'public',
    details: {
      confidence,
      threshold: thresh,
      publication_class: decision.classification,
      publication_score: decision.score,
      message_time_ms: ctx.messageTimeMs,
    },
  };
}

export function markerPassesPublicMapRawFilter(
  m: Record<string, unknown>,
  ctx: PublicMapRawFilterContext,
): boolean {
  return explainPublicMapRawFilter(m, ctx).passes;
}
