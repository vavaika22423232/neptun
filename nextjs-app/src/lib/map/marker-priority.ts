import type { Marker } from '@/types';

/**
 * Вище = важливіше для `symbol-sort-key` (малюється поверх інших).
 * Діапазон ~0–800 достатній для step/sort.
 */
export function markerVisualPriority(marker: Marker): number {
  const t = (marker.threat_type || '').toLowerCase();
  let score = 200;

  if (
    t.includes('ballistic') ||
    t.includes('missile') ||
    t.includes('rocket') ||
    t === 'kinzhal' ||
    t === 'iskander'
  ) {
    score += 320;
  } else if (t === 'shahed' || t === 'drone' || t === 'uav' || t === 'default') {
    score += 120;
  } else if (t.includes('cruise') || t.includes('kalibr')) {
    score += 200;
  }

  const phase = marker.flight_phase;
  if (phase === 'approach') score += 90;
  else if (phase === 'circling') score += 50;

  const dc = marker.display_class;
  if (dc === 'corroborated_point') score += 55;
  else if (dc === 'corridor_or_bearing') score += 25;
  else if (dc === 'region_signal') score -= 45;

  let epochMs = 0;
  if (marker.last_update_epoch) {
    epochMs = marker.last_update_epoch > 10000000000 ? marker.last_update_epoch : marker.last_update_epoch * 1000;
  } else if (marker.created_at_epoch) {
    epochMs = marker.created_at_epoch > 10000000000 ? marker.created_at_epoch : marker.created_at_epoch * 1000;
  } else if (marker.date) {
    epochMs = new Date(marker.date).getTime();
  }
  if (epochMs) {
    const ageMin = (Date.now() - epochMs) / 60000;
    if (ageMin < 2) score += 130;
    else if (ageMin < 8) score += 75;
    else if (ageMin < 20) score += 25;
    else score -= 40;
  }

  const c100 = marker.confidence_0_100;
  if (c100 != null && Number.isFinite(c100) && c100 < 55) score -= 35;
  else if (marker.confidence != null && Number.isFinite(marker.confidence) && marker.confidence < 0.55) {
    score -= 35;
  }

  return Math.max(0, Math.min(920, score));
}
