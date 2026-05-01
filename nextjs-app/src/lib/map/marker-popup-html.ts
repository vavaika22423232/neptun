import type { Marker } from '@/types';
import { THREAT_NAMES } from '@/types';
import { resolveThreatBearingDeg } from '@/lib/threat-bearing';

/** ISO timestamp → Kyiv time (HH:MM DD.MM.YYYY) */
export function formatKyivTime(isoStr: string): string {
  try {
    const d = new Date(isoStr);
    if (isNaN(d.getTime())) return isoStr;
    return d.toLocaleString('uk-UA', {
      timeZone: 'Europe/Kyiv',
      hour: '2-digit',
      minute: '2-digit',
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
  } catch {
    return isoStr;
  }
}

/**
 * HTML для Leaflet.Popup / MapLibre.Popup (адмін-кнопки покладаються на window.__admin*).
 * Розмітка компактна; стилі — `map-neptun.css` (.neptun-popup*).
 */
export function buildMarkerPopup(marker: Marker, threatType: string, isAdminUser: boolean): string {
  const typeName = THREAT_NAMES[threatType] || threatType;
  const trustEsc = (marker.display_trust_hint_uk || '').replace(/</g, '&lt;');
  const trustBlock = trustEsc ? `<div class="neptun-popup__trust">${trustEsc}</div>` : '';
  const trackStateLabel: Record<string, string> = {
    observed: 'Підтверджене свіже спостереження',
    extrapolated: 'Прогнозована позиція за останнім курсом',
    stale: 'Застарілий трек, позиція приглушена',
    lost: 'Трек втрачено, рух зупинено',
    static: 'Статична подія',
    manual: 'Ручна позначка оператора',
    split_candidate: 'Конфлікт координат, потрібне підтвердження',
  };
  const trackState = marker.track_state;
  const trackBlock = trackState
    ? `<div class="neptun-popup__meta">${trackStateLabel[trackState] || trackState}${
        marker.track_confidence != null && Number.isFinite(marker.track_confidence)
          ? ` · довіра ${Math.round(Math.max(0, Math.min(1, marker.track_confidence)) * 100)}%`
          : ''
      }</div>`
    : '';
  const placeEsc = (marker.place || 'Невідомо').replace(/</g, '&lt;');
  const brg = resolveThreatBearingDeg(marker);
  const courseBlock =
    brg != null
      ? `<div class="neptun-popup__meta">Курс ~${Math.round(brg)}° (за даними карти)</div>`
      : '';
  const dateBlock = marker.date ? `<div class="neptun-popup__time">${formatKyivTime(marker.date)}</div>` : '';

  let actions = '';
  if (isAdminUser) {
    const markerId = (marker.id || '').replace(/'/g, "\\'");
    const markerLat = marker.lat;
    const markerLng = marker.lng;
    const markerText = (marker.text || '').replace(/'/g, "\\'").replace(/\n/g, ' ').substring(0, 80);
    actions = `<div class="neptun-popup__actions">
        <button type="button" class="neptun-popup__btn neptun-popup__btn--danger" onclick="window.__adminDeleteMarker('${markerId}',${markerLat},${markerLng},'${markerText}')">
          <span class="material-icons" aria-hidden="true">delete</span>Видалити
        </button>
        <button type="button" class="neptun-popup__btn neptun-popup__btn--muted" onclick="window.__adminHideMarker(${markerLat},${markerLng},'${markerText}')">
          <span class="material-icons" aria-hidden="true">visibility_off</span>Сховати
        </button>
      </div>`;
  }

  return `<div class="neptun-popup">
      ${trustBlock}
      <div class="neptun-popup__title">${typeName}</div>
      <div class="neptun-popup__place">${placeEsc}</div>
      ${trackBlock}
      ${courseBlock}
      ${dateBlock}
      ${actions}
    </div>`;
}
