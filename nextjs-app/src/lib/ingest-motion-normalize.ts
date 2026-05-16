import { trackMotionProfile } from '@/lib/track-motion-profile';

/**
 * Clamps ingest `speed_kmh` to the threat motion profile max so worker/LLM spikes
 * do not distort correlator gates, admin feeds, or client displays.
 */
export function normalizeIngestMotionFields(marker: Record<string, unknown>): void {
  const threatType = String(marker.threat_type || marker.type || '');
  const speed = Number(marker.speed_kmh);
  if (!Number.isFinite(speed) || speed <= 0) return;
  const profile = trackMotionProfile(threatType);
  if (speed > profile.maxSpeedKmh) {
    marker.speed_kmh = profile.maxSpeedKmh;
  }
}

/**
 * PATCH `/api/ingest` і адмін-оновлення: обрізає `speed_kmh` у частковому апдейті.
 */
export function normalizeIngestMotionPatch(
  updates: Record<string, unknown>,
  threatTypeHint: string | undefined,
): void {
  if (!('speed_kmh' in updates)) return;
  const speed = Number(updates.speed_kmh);
  if (!Number.isFinite(speed) || speed <= 0) return;
  const profile = trackMotionProfile(threatTypeHint || '');
  if (speed > profile.maxSpeedKmh) {
    updates.speed_kmh = profile.maxSpeedKmh;
  }
}
