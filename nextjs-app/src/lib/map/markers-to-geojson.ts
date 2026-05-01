import type { Marker } from '@/types';
import { THREAT_ICONS } from '@/types';
import { CACHE_VERSION } from '@/lib/constants';
import { bearingToWebIconRotationCssDeg, resolveThreatBearingDeg } from '@/lib/threat-bearing';
import { markerVisualPriority } from '@/lib/map/marker-priority';

const MAP_BOUNDS = { minLat: 44.2, maxLat: 52.4, minLng: 22.0, maxLng: 40.2 } as const;

/** Стабільний ключ треку / маркера (узгоджено з Leaflet MapContainer). */
export function stableMarkerKey(m: Marker): string {
  const tid = m.track_id != null && String(m.track_id).trim().length > 0 ? String(m.track_id).trim() : '';
  if (tid) return `t:${tid}`;
  const id = m.id != null && String(m.id).trim().length > 0 ? String(m.id).trim() : '';
  if (id) return `i:${id}`;
  const lat = Number(m.lat);
  const lng = Number(m.lng);
  if (Number.isFinite(lat) && Number.isFinite(lng)) {
    return `p:${lat.toFixed(3)}_${lng.toFixed(3)}_${m.threat_type || 'x'}`;
  }
  return `u:${Math.random().toString(36).slice(2)}`;
}

export function combinedMarkerOpacity(marker: Marker): number {
  void marker;
  return 1;
}

/** Сирі дані API без display policy → узгоджено з Leaflet `normalizeMarkerDisplay`. */
export function normalizeMarkerDisplayForMap(marker: Marker): Marker {
  if (
    marker.display_class &&
    typeof marker.show_precise_pin === 'boolean' &&
    typeof marker.display_uncertainty_km === 'number'
  ) {
    return marker;
  }
  return {
    ...marker,
    display_class: 'corroborated_point',
    show_precise_pin: true,
    display_uncertainty_km: 0,
    display_trust_hint_uk: marker.display_trust_hint_uk ?? '',
  };
}

/** Ім’я зображення для MapLibre `icon-image` (лише [a-z0-9_]). */
export function maplibreIconId(marker: Marker): string {
  const threatType = marker.threat_type || 'default';
  const iconFile = marker.marker_icon || THREAT_ICONS[threatType] || 'shahed3.webp';
  const base = `${threatType}_${iconFile}`.replace(/[^a-zA-Z0-9]+/g, '_').toLowerCase();
  return base.length > 120 ? base.slice(0, 120) : base;
}

/** Публічний URL іконки (кеш у query). */
export function markerIconUrl(marker: Marker): string {
  const threatType = marker.threat_type || 'default';
  const iconFile = marker.marker_icon || THREAT_ICONS[threatType] || 'shahed3.webp';
  return `/${iconFile}?${CACHE_VERSION}`;
}

/** Розмір піна в px — узгоджено з Leaflet `buildThreatDivIcon`. */
export function threatIconDisplayPx(marker: Marker): number {
  const threatType = marker.threat_type || 'default';
  const iconFile = marker.marker_icon || THREAT_ICONS[threatType] || 'shahed3.webp';
  const isShahed =
    threatType === 'shahed' ||
    threatType === 'drone' ||
    threatType === 'uav' ||
    threatType === 'default';
  let size = isShahed ? 44 : 32;
  if (/fpvdrone/i.test(iconFile)) size = Math.round(size / 2);
  if (iconFile === 'shahed3.webp' || iconFile === 'icon_missile.svg') {
    size = Math.max(16, Math.round(size / 1.5));
    size = Math.round(size * 1.2);
  }
  if (iconFile === 'icon_tu95.svg') {
    return 54;
  }
  return size;
}

export type ThreatPointFeature = {
  type: 'Feature';
  id?: string;
  geometry: { type: 'Point'; coordinates: [number, number] };
  properties: {
    mid: string;
    micon: string;
    bearing: number;
    opacity: number;
    icon_px: number;
    prio: number;
    threat_type: string;
    _m: string;
  };
};

export type ThreatMarkerFeatureCollection = {
  type: 'FeatureCollection';
  features: ThreatPointFeature[];
};

/**
 * Маркери → GeoJSON для шару загроз (MapLibre `threats`).
 * У properties зберігаємо мінімум для popup після кліку (повний об’єкт як JSON).
 */
export function markersToGeoJSON(markers: Marker[]): ThreatMarkerFeatureCollection {
  const features: ThreatPointFeature[] = [];

  for (const rawIn of markers) {
    const raw = normalizeMarkerDisplayForMap(rawIn);
    const lat = parseFloat(String(raw.lat));
    const lng = parseFloat(String(raw.lng));
    if (isNaN(lat) || isNaN(lng)) continue;
    if (lat < MAP_BOUNDS.minLat || lat > MAP_BOUNDS.maxLat || lng < MAP_BOUNDS.minLng || lng > MAP_BOUNDS.maxLng) {
      continue;
    }

    const key = stableMarkerKey(raw);
    const brg = resolveThreatBearingDeg(raw);
    const rotation = brg != null ? bearingToWebIconRotationCssDeg(brg) : 0;
    const micon = maplibreIconId(raw);
    const opacity = combinedMarkerOpacity(raw);
    const prio = markerVisualPriority(raw);
    const icon_px = threatIconDisplayPx(raw);

    features.push({
      type: 'Feature',
      id: key,
      geometry: { type: 'Point', coordinates: [lng, lat] },
      properties: {
        mid: key,
        micon,
        bearing: rotation,
        opacity,
        icon_px,
        prio,
        threat_type: raw.threat_type || 'default',
        /** серіалізація для popup */
        _m: JSON.stringify(raw),
      },
    });
  }

  return { type: 'FeatureCollection', features };
}
