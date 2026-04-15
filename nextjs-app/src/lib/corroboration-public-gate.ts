/**
 * Shared rules for when corroboration_pending should gate the public map / SSE.
 * Phantom avia (synthetic airfield pin for KAB) always requires the same 2-source
 * bar as dualSourceMapGate, even when that global setting is off.
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
