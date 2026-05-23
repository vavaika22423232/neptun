import type { ThreatMarker } from '../../../types/map';
import { parseThreatMarker } from '../utils/parseThreatMarker';

/**
 * Flutter `ThreatMarker.applyPartialUpdate` parity for SSE marker_update / track_update.
 */
export function applyMarkerPatch(
  current: ThreatMarker,
  updates: Record<string, unknown>,
): ThreatMarker {
  const base = { ...current } as ThreatMarker & Record<string, unknown>;
  for (const [key, value] of Object.entries(updates)) {
    if (key === 'id') continue;
    if (value != null && typeof value === 'object' && !Array.isArray(value)) {
      const prev = base[key];
      base[key] =
        prev != null && typeof prev === 'object' && !Array.isArray(prev)
          ? { ...(prev as Record<string, unknown>), ...(value as Record<string, unknown>) }
          : value;
    } else {
      base[key] = value;
    }
  }
  return parseThreatMarker(base) ?? current;
}
