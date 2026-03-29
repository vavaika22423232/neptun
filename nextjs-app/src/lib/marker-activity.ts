import type { Marker } from '@/types';

/** Last meaningful telemetry time for sorting / UI (matches MapContainer logic). */
export function getLastActivityMs(marker: Marker): number {
  const obs = marker.observations as Array<{ ts: number }> | undefined;
  if (obs && obs.length > 0) {
    const t = obs[obs.length - 1].ts;
    if (typeof t === 'number' && t > 1e11) return t;
  }
  if (marker.positions?.length) {
    const last = marker.positions[marker.positions.length - 1];
    if (typeof last.ts === 'number' && last.ts > 1e11) return last.ts;
  }
  if (typeof marker.last_update_epoch === 'number' && marker.last_update_epoch > 1e11) {
    return marker.last_update_epoch;
  }
  const c = marker.created_at_epoch as number | undefined;
  if (typeof c === 'number' && c > 1e11) return c;
  if (marker.date) {
    const d = new Date(marker.date).getTime();
    if (!isNaN(d)) return d;
  }
  return 0;
}
