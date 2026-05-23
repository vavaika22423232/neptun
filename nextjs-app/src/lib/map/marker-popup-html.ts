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

function sanitizeCssSegment(raw: string): string {
  const s = raw.replace(/[^a-z0-9_-]/gi, '');
  return s.length > 0 ? s : 'x';
}

/** Прибираємо провідні емодзі з `THREAT_NAMES` — у попапі показуємо текст без «🛩️». */
function stripLeadingEmoji(s: string): string {
  return s.replace(/^[\s\uFE0F]*(?:\p{Extended_Pictographic}[\uFE0F\u200D]*)+/gu, '').trim();
}

const TRACK_LABELS: Record<string, string> = {
  observed: 'Свіже спостереження',
  extrapolated: 'Екстраполяція за курсом',
  stale: 'Застарілий трек',
  lost: 'Трек втрачено',
  static: 'Статична подія',
  manual: 'Позначка оператора',
  split_candidate: 'Потрібне підтвердження',
};

const QUALITY_LABELS: Record<string, string> = {
  observed: 'фіксація',
  estimated: 'оцінка',
  coarse: 'район',
  target_hint: 'курс/ціль',
};

/**
 * HTML для MapLibre.Popup (адмін-кнопки на window.__admin*).
 * Класи `.neptun-popup-card*` — у `globals.css`.
 */
export function buildMarkerPopup(marker: Marker, threatType: string, isAdminUser: boolean): string {
  const typeName = stripLeadingEmoji(THREAT_NAMES[threatType] || threatType);
  const trustEsc = (marker.display_trust_hint_uk || '').replace(/</g, '&lt;');
  const trustBlock = trustEsc
    ? `<div class="neptun-popup-card__trust" role="note">${trustEsc}</div>`
    : '';

  // ── Track state + pills ───────────────────────────────────────────────────
  const trackState = marker.track_state;
  const stateSeg = trackState ? sanitizeCssSegment(trackState) : '';
  const stateLabel = trackState ? TRACK_LABELS[trackState] || trackState : '';
  let confidenceFrag = '';
  if (trackState && marker.track_confidence != null && Number.isFinite(marker.track_confidence)) {
    confidenceFrag = ` · ${Math.round(Math.max(0, Math.min(1, marker.track_confidence)) * 100)}%`;
  }

  const loiteringPill = marker.is_loitering
    ? `<span class="neptun-popup-card__pill neptun-popup-card__pill--loitering">⟳ Барражує</span>`
    : '';
  const estimatedPill = marker.position_estimated
    ? `<span class="neptun-popup-card__pill neptun-popup-card__pill--estimated">~ Позиція</span>`
    : '';
  const qualityPill = marker.last_observation_quality
    ? `<span class="neptun-popup-card__pill neptun-popup-card__pill--estimated">${QUALITY_LABELS[marker.last_observation_quality] || marker.last_observation_quality}</span>`
    : '';

  const statusRow =
    trackState && stateLabel
      ? `<div class="neptun-popup-card__status-row">
          <span class="neptun-popup-card__pill neptun-popup-card__pill--${stateSeg}">${stateLabel}${confidenceFrag}</span>
          ${loiteringPill}${estimatedPill}${qualityPill}
        </div>`
      : '';

  // ── Place ─────────────────────────────────────────────────────────────────
  const placeEsc = (marker.place || 'Невідомо').replace(/</g, '&lt;');

  // ── Heading / course ──────────────────────────────────────────────────────
  const brg = resolveThreatBearingDeg(marker);
  const confLabel =
    marker.heading_confidence === 'track'    ? 'підтверджений трек' :
    marker.heading_confidence === 'explicit' ? 'явний з тексту' :
    marker.heading_confidence === 'regional' ? '≈ регіональний коридор' :
    'невідомо';

  const courseRow = brg != null
    ? `<div class="neptun-popup-card__row">
        <span class="neptun-popup-card__row-label">Курс</span>
        <span class="neptun-popup-card__row-value">${Math.round(brg)}°</span>
      </div>`
    : '';

  const truth = marker.tracker_truth;
  const uncertaintyRow = truth?.confidence_radius_km != null
    ? `<div class="neptun-popup-card__row">
        <span class="neptun-popup-card__row-label">Точність</span>
        <span class="neptun-popup-card__row-value">±${Math.round(truth.confidence_radius_km)} км</span>
      </div>`
    : '';

  // ── ETA ──────────────────────────────────────────────────────────────────
  let etaRow = '';

  // ── Date ──────────────────────────────────────────────────────────────────
  const dateRow = marker.date
    ? `<div class="neptun-popup-card__footer">
          <time class="neptun-popup-card__time" datetime="${String(marker.date).replace(/"/g, '&quot;')}">${formatKyivTime(marker.date)}</time>
        </div>`
    : '';

  // ── Admin actions ─────────────────────────────────────────────────────────
  let actions = '';
  if (isAdminUser) {
    const markerId = (marker.id || '').replace(/'/g, "\\'");
    const markerLat = marker.lat;
    const markerLng = marker.lng;
    const markerText = (marker.text || '').replace(/'/g, "\\'").replace(/\n/g, ' ').substring(0, 80);
    actions = `<div class="neptun-popup-card__actions">
        <button type="button" class="neptun-popup-card__btn neptun-popup-card__btn--danger" onclick="window.__adminDeleteMarker('${markerId}',${markerLat},${markerLng},'${markerText}')">
          <span class="material-icons" aria-hidden="true">delete</span>Видалити
        </button>
        <button type="button" class="neptun-popup-card__btn neptun-popup-card__btn--muted" onclick="window.__adminHideMarker(${markerLat},${markerLng},'${markerText}')">
          <span class="material-icons" aria-hidden="true">visibility_off</span>Сховати
        </button>
      </div>`;
  }


  return `<article class="neptun-popup-card">
      ${trustBlock}
      <div class="neptun-popup-card__main">
        <header class="neptun-popup-card__header">
          <p class="neptun-popup-card__category">${typeName}</p>
          <h2 class="neptun-popup-card__headline">${placeEsc}</h2>
        </header>
        ${statusRow}
        ${courseRow}
        ${uncertaintyRow}
        ${etaRow}
        ${dateRow}
      </div>
      ${actions}
    </article>`;
}
