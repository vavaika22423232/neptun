/**
 * Shared constants and pure helpers used by both marker-publication.ts and public-marker-policy.ts.
 * Single source of truth — change here, applies everywhere.
 * Intentionally has NO imports to avoid circular dependency chains.
 */

export const UAV_PUBLICATION_TYPES = new Set([
  'shahed',
  'drone',
  'uav',
  'fpv',
  'rozved',
  'air_balloon',
]);

/**
 * Message text patterns that indicate post-strike reconnaissance (дорозвідка).
 * These are admin-only: the attack is already over, a drone is checking results.
 * Regular розвідка (scouting ahead of an attack) is still public.
 */
export const POST_STRIKE_RECON_PATTERNS = [
  /дорозвідк/i,
  /до-?розвідк/i,
  /post.?strike.?recon/i,
];

/**
 * Resolve statuses that are never suitable for the public map
 * (too vague / area-only / no point resolution).
 */
export const NON_PUBLIC_RESOLVE_STATUSES = new Set([
  'oblast_fallback',
  'oblast_direction_only',
  'estimated_oblast_center',
  'estimated_offset_coastal',
  'ambiguous_no_point',
  'target_only_no_current_position',
  'weak_target_only_no_point',
  // Centroid placements from regional nickname recognition (e.g. "Кіровоградщина")
  'regional_oblast_centroid',
  'regional_oblast_direction_target',
]);

/**
 * Normalized place name tokens that indicate a non-specific / unsafe locality.
 * A marker whose place matches any of these is gated from the public map.
 */
/**
 * P3-B: Pure phantom-avia checker — moved here from marker-publication.ts to break
 * the circular import (public-marker-policy → marker-publication → public-marker-policy).
 */
export function recordHasPhantomAvia(
  record: Record<string, unknown>,
  marker?: Record<string, unknown>,
): boolean {
  const fromMarker =
    marker && typeof marker.resolve_status === 'string' ? marker.resolve_status : '';
  const fromRecord = typeof record.resolve_status === 'string' ? record.resolve_status : '';
  const rs = (fromMarker || fromRecord).toLowerCase();
  return rs.includes('phantom_avia');
}

export const BAD_PLACE_TOKENS = new Set([
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
