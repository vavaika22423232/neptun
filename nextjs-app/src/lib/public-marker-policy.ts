import crypto from 'crypto';
import type { AdminSettings } from '@/lib/admin/data';
import { isPlausibleThreatCoordinate } from '@/lib/geo-bounds';
import { isPublicMapThreatGeography } from '@/lib/public-threat-geo';
import { recordHasPhantomAvia } from '@/lib/marker-publication';

export type MarkerPublicationClass =
  | 'VERIFIED_PUBLIC'
  | 'ADMIN_ONLY'
  | 'QUARANTINED'
  | 'REJECTED';

export type MarkerPublicationScores = {
  extraction: number;
  locality: number;
  source: number;
  motion: number;
  evidence: number;
  publication: number;
};

export type MarkerPublicationDecision = {
  classification: MarkerPublicationClass;
  public: boolean;
  score: number;
  scores: MarkerPublicationScores;
  fingerprint: string;
  reasons: string[];
  invariantViolations: string[];
};

export type MarkerPublicationContext = {
  settings: AdminSettings;
  nowMs?: number;
  hidden?: boolean;
};

const PUBLIC_THRESHOLD = 0.82;
const ADMIN_THRESHOLD = 0.7;
const QUARANTINE_THRESHOLD = 0.4;

const UAV_PUBLICATION_TYPES = new Set([
  'shahed',
  'drone',
  'uav',
  'fpv',
  'rozved',
  'air_balloon',
]);

const NON_PUBLIC_RESOLVE_STATUSES = new Set([
  'oblast_fallback',
  'oblast_direction_only',
  'estimated_oblast_center',
  'estimated_offset_coastal',
  'ambiguous_no_point',
  'target_only_no_current_position',
  'weak_target_only_no_point',
]);

const BAD_PLACE_TOKENS = new Set([
  'вода',
  'воді',
  'воду',
  'водою',
  'воде',
  'water',
  'море',
  'морем',
  'морі',
  'морю',
  'акваторія',
  'акваторії',
  'акваторию',
  'поле',
  'полях',
  'ліс',
  'лісі',
  'лес',
  'район',
  'району',
  'районі',
  'область',
  'області',
  'місто',
  'село',
  'селище',
  'невідомо',
  'unknown',
]);

function clamp01(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.min(1, Math.max(0, value));
}

function normalizeText(value: unknown): string {
  return String(value || '')
    .normalize('NFKC')
    .trim()
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s'ʼ:._-]/gu, '')
    .replace(/\s+/g, ' ');
}

function stableJson(value: unknown): string {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map((v) => stableJson(v)).join(',')}]`;
  const obj = value as Record<string, unknown>;
  return `{${Object.keys(obj).sort().map((k) => `${JSON.stringify(k)}:${stableJson(obj[k])}`).join(',')}}`;
}

function candidateCount(marker: Record<string, unknown>): number {
  if (typeof marker.candidates_count === 'number' && Number.isFinite(marker.candidates_count)) {
    return Math.max(0, marker.candidates_count);
  }
  return Array.isArray(marker.candidates) ? marker.candidates.length : 0;
}

function markerConfidence(marker: Record<string, unknown>, settings: AdminSettings): number {
  const targetConfidence = Number(marker.target_confidence);
  if (normalizeText(marker.target_lifecycle_state) && Number.isFinite(targetConfidence)) {
    return clamp01(targetConfidence);
  }
  if (typeof marker.confidence === 'number' && Number.isFinite(marker.confidence)) {
    return clamp01(marker.confidence);
  }
  if (typeof marker.confidence_0_100 === 'number' && Number.isFinite(marker.confidence_0_100)) {
    return clamp01(marker.confidence_0_100 / 100);
  }
  const t = normalizeText(marker.threat_type || marker.type);
  if (UAV_PUBLICATION_TYPES.has(t) && typeof settings.minConfidenceUav === 'number') {
    return clamp01(settings.minConfidenceUav);
  }
  return clamp01(settings.minConfidence ?? 0.65);
}

export function computeMarkerEventFingerprint(marker: Record<string, unknown>): string {
  const raw = {
    channel: normalizeText(marker.channel_name || marker.channel),
    msg_id: marker.msg_id ?? marker.message_id ?? '',
    text: normalizeText(marker.text),
    threat_type: normalizeText(marker.threat_type || marker.type),
    place: normalizeText(marker.place || marker.city || marker.location),
    region: normalizeText(marker.region || marker.oblast),
    created_at_epoch: marker.created_at_epoch ?? marker.timestamp ?? marker.ts ?? '',
  };
  return crypto.createHash('sha256').update(stableJson(raw)).digest('hex').slice(0, 32);
}

export function markerHasAmbiguousGeocode(marker: Record<string, unknown>): boolean {
  const tier = normalizeText(marker.geocode_tier);
  if (tier === 'multi' || tier === 'ambiguous') return true;
  if (candidateCount(marker) > 1) return true;

  const rs = normalizeText(marker.resolve_status).replace(/\s+/g, '_');
  if (NON_PUBLIC_RESOLVE_STATUSES.has(rs)) return true;
  return rs.includes('ambiguous') || rs.includes('multi');
}

export function markerHasNonPublicPlaceLabel(marker: Record<string, unknown>): boolean {
  const place = normalizeText(marker.place || marker.city || marker.location);
  if (!place) return false;
  if (BAD_PLACE_TOKENS.has(place)) return true;

  const compact = place.replace(/[\s'ʼ._:-]+/g, '');
  if (BAD_PLACE_TOKENS.has(compact)) return true;
  return compact.length < 3 && !/^\d+$/.test(compact);
}

function markerBlockedByPublicPlacementQuality(marker: Record<string, unknown>): boolean {
  const pm = normalizeText(marker.placement_mode);
  if (pm === 'approximate') return true;
  if (pm === 'predictive') return false;
  if (markerHasAmbiguousGeocode(marker)) return true;
  if (markerHasNonPublicPlaceLabel(marker)) return true;
  return false;
}

function localityConfidence(marker: Record<string, unknown>, reasons: string[]): number {
  if (marker.manual === true) return 1;
  const lat = Number(marker.lat);
  const lng = Number(marker.lng);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
    reasons.push('invalid_coords');
    return 0;
  }
  if (!isPlausibleThreatCoordinate(lat, lng)) {
    reasons.push('implausible_coords');
    return 0;
  }
  if (!isPublicMapThreatGeography(lat, lng)) {
    reasons.push('outside_public_threat_geography');
    return 0;
  }
  if (markerHasNonPublicPlaceLabel(marker)) {
    reasons.push('non_public_place_label');
    return 0.2;
  }
  if (markerHasAmbiguousGeocode(marker)) {
    reasons.push('ambiguous_geocode');
    return 0.45;
  }
  const pm = normalizeText(marker.placement_mode);
  if (pm === 'approximate') {
    reasons.push('approximate_coordinates');
    return 0.55;
  }
  if (pm === 'predictive') {
    reasons.push('predictive_not_point');
    return 0.7;
  }

  const rs = normalizeText(marker.resolve_status);
  if (!rs || rs === 'ok' || rs === 'exact' || rs === 'point') return 0.95;
  if (rs.includes('regeocode') || rs.includes('coherence')) return 0.82;
  return 0.75;
}

function sourceConfidence(marker: Record<string, unknown>, settings: AdminSettings): number {
  if (marker.manual === true) return 1;
  const observations = Array.isArray(marker.observations) ? marker.observations : [];
  if (observations.some((o) => Number((o as Record<string, unknown>).channel_priority) <= 1)) return 0.95;
  const sources = new Set(
    observations
      .map((o) => normalizeText((o as Record<string, unknown>).source))
      .filter(Boolean),
  );
  const sourceCount = Number(marker.source_count);
  if (Number.isFinite(sourceCount) && sourceCount >= 2) return 0.95;
  if (sources.size >= 2) return 0.95;
  const priority = Number(marker.channel_priority);
  if (Number.isFinite(priority) && priority <= 1) return 0.95;
  if (Number.isFinite(priority) && priority <= 3) return 0.85;

  // If dual source gate is OFF, single source is allowed to be public (0.95 score)
  if (settings.dualSourceMapGate === false) return 0.95;

  // HIGH CONFIDENCE BYPASS: if the parser is extremely certain (e.g. 90%+), 
  // allow it even if single source by scoring it high enough to pass the threshold.
  const extraction = markerConfidence(marker, settings);
  if (extraction >= 0.88) return 0.88;

  return 0.75;
}

function motionConfidence(marker: Record<string, unknown>, reasons: string[]): number {
  if (marker.manual === true) return 1;
  const lifecycle = normalizeText(marker.target_lifecycle_state);
  const isConfirmedTarget = lifecycle === 'confirmed';
  if (lifecycle && lifecycle !== 'confirmed') {
    reasons.push(`target_${lifecycle}`);
    if (lifecycle === 'destroyed' || lifecycle === 'rejected' || lifecycle === 'lost' || lifecycle === 'stale') {
      return 0;
    }
    return 0.7;
  }
  const state = normalizeText(marker.track_state);
  if (state === 'lost' || state === 'split_candidate') {
    reasons.push(`track_${state}`);
    return 0;
  }
  if (state === 'stale' || state === 'extrapolated') {
    reasons.push(`track_${state}`);
    if (state === 'extrapolated' && isConfirmedTarget) return 0.95;
    return 0.65;
  }
  if (typeof marker.track_confidence === 'number' && Number.isFinite(marker.track_confidence)) {
    return clamp01(marker.track_confidence);
  }
  return 0.95;
}

function evidenceConfidence(marker: Record<string, unknown>, reasons: string[], settings: AdminSettings): number {
  if (marker.manual === true) return 1;
  const targetConfidence = Number(marker.target_confidence);
  if (Number.isFinite(targetConfidence)) return clamp01(targetConfidence);
  if (recordHasPhantomAvia(marker)) {
    reasons.push('synthetic_marker');
    return 0.25;
  }
  const observations = Array.isArray(marker.observations) ? marker.observations : [];
  const sources = new Set(
    observations
      .map((o) => normalizeText((o as Record<string, unknown>).source))
      .filter(Boolean),
  );
  if (observations.some((o) => Number((o as Record<string, unknown>).channel_priority) <= 1)) return 0.95;
  if (sources.size >= 2) return 0.95;

  // If dual source gate is OFF, single source evidence is enough for public
  if (settings.dualSourceMapGate === false) return 0.95;

  const sourceCount = Number(marker.source_count);
  if (Number.isFinite(sourceCount) && sourceCount >= 2) return 0.95;
  if (sources.size === 1) return 0.82;
  return normalizeText(marker.channel_name || marker.channel) ? 0.78 : 0.65;
}

function classify(score: number, invariantViolations: string[], publicBlocked: boolean): MarkerPublicationClass {
  const hardReject = invariantViolations.some((v) =>
    v === 'invalid_coords' ||
    v === 'hidden_marker' ||
    v === 'lost_or_split_track' ||
    v === 'outside_public_threat_geography'
  );
  if (hardReject) return 'REJECTED';
  if (!publicBlocked && score >= PUBLIC_THRESHOLD) return 'VERIFIED_PUBLIC';
  if (score >= ADMIN_THRESHOLD) return 'ADMIN_ONLY';
  if (score >= QUARANTINE_THRESHOLD) return 'QUARANTINED';
  return 'REJECTED';
}

export function evaluateMarkerPublication(
  marker: Record<string, unknown>,
  ctx: MarkerPublicationContext,
): MarkerPublicationDecision {
  const reasons: string[] = [];
  const invariantViolations: string[] = [];

  const extraction = markerConfidence(marker, ctx.settings);
  const locality = localityConfidence(marker, reasons);
  const source = sourceConfidence(marker, ctx.settings);
  const motion = motionConfidence(marker, reasons);
  const evidence = evidenceConfidence(marker, reasons, ctx.settings);
  const score = Math.min(extraction, locality, source, motion, evidence);

  if (ctx.hidden || marker.hidden === true) invariantViolations.push('hidden_marker');
  if (locality <= 0) invariantViolations.push('invalid_coords');
  if (reasons.includes('outside_public_threat_geography')) invariantViolations.push('outside_public_threat_geography');
  if (reasons.includes('track_lost') || reasons.includes('track_split_candidate')) invariantViolations.push('lost_or_split_track');
  if (reasons.some((r) => r.startsWith('target_') && r !== 'target_confirmed')) invariantViolations.push('target_not_confirmed');
  if (markerBlockedByPublicPlacementQuality(marker)) invariantViolations.push('unsafe_locality');
  if (recordHasPhantomAvia(marker)) invariantViolations.push('synthetic_marker');

  const publicBlocked =
    invariantViolations.length > 0 ||
    markerBlockedByPublicPlacementQuality(marker) ||
    normalizeText(marker.placement_mode) === 'predictive';

  const classification = marker.manual === true
    ? 'VERIFIED_PUBLIC'
    : classify(score, invariantViolations, publicBlocked);

  return {
    classification,
    public: classification === 'VERIFIED_PUBLIC',
    score,
    scores: {
      extraction,
      locality,
      source,
      motion,
      evidence,
      publication: score,
    },
    fingerprint: typeof marker.event_fingerprint === 'string'
      ? marker.event_fingerprint
      : computeMarkerEventFingerprint(marker),
    reasons: Array.from(new Set(reasons)),
    invariantViolations: Array.from(new Set(invariantViolations)),
  };
}
