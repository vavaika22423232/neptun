import type { ThreatMarker } from '../../../types/map';

export type ThreatSheetStatus = { label: string; color: string };

export function resolveThreatSheetStatus(raw: Record<string, unknown>, marker: ThreatMarker): ThreatSheetStatus {
  const state = String(raw.track_state ?? '').toLowerCase();
  const epochMs = typeof raw.last_update_epoch === 'number' ? raw.last_update_epoch : Number(raw.last_update_epoch);
  const staleByAge =
    Number.isFinite(epochMs) &&
    epochMs > 0 &&
    Date.now() - (epochMs < 20000000000 ? epochMs * 1000 : epochMs) > 30 * 60 * 1000;

  if (state === 'stale' || state === 'lost' || staleByAge) {
    return { label: 'Застаріле уточнення', color: '#78716C' };
  }
  if (state === 'extrapolated') {
    return { label: 'Оновлено (оцінка руху)', color: '#0F766E' };
  }
  if (state === 'observed') {
    return { label: 'Спостерігається', color: '#0F766E' };
  }

  const pm = (marker.placementMode ?? '').toLowerCase();
  if (pm.includes('approx') || pm.includes('predict') || pm.includes('region')) {
    return { label: 'Приблизно на карті', color: '#B45309' };
  }

  return { label: 'Активне позначення', color: '#00668a' };
}
