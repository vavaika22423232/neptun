import type { Marker } from '@/types';
import { THREAT_ICONS } from '@/types';
import { CACHE_VERSION } from '@/lib/constants';
import { bearingToWebIconRotationCssDeg, resolveThreatBearingDeg } from '@/lib/threat-bearing';
import { markerVisualPriority } from '@/lib/map/marker-priority';
import { expandMarkersForSwarmDisplay } from '@/lib/map/marker-swarm-expand';
import { markerBehavior, markerPassesMapDisplayAge } from '@/lib/marker-behavior';

import { MAP_BOUNDS } from '@/lib/map/map-bounds';

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
    halo_opacity: number;
    halo_radius: number;
    halo_color: string;
    behavior: string;
    prio: number;
    threat_type: string;
    count: number;
    count_label: string;
    badge_color: string;
    status_label: string;
    observation_quality: string;
    text_intent: string;
    coordinate_role: string;
    public_position_policy: string;
    threat_zone_radius_km: number;
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
  const expanded = expandMarkersForSwarmDisplay(markers);

  for (const rawIn of expanded) {
    const raw = normalizeMarkerDisplayForMap(rawIn);
    if (!markerPassesMapDisplayAge(raw)) continue;
    const lat = parseFloat(String(raw.rendered_lat ?? raw.lat));
    const lng = parseFloat(String(raw.rendered_lng ?? raw.lng));
    if (isNaN(lat) || isNaN(lng)) continue;
    if (lat < MAP_BOUNDS.minLat || lat > MAP_BOUNDS.maxLat || lng < MAP_BOUNDS.minLng || lng > MAP_BOUNDS.maxLng) {
      continue;
    }

    const key = stableMarkerKey(raw);
    const brg = resolveThreatBearingDeg(raw);
    const rotation = brg != null ? bearingToWebIconRotationCssDeg(brg) : 0;
    const micon = maplibreIconId(raw);
    const behavior = markerBehavior(raw);
    const opacity = behavior.opacity;
    const prio = markerVisualPriority(raw);
    const icon_px = Math.round(threatIconDisplayPx(raw) * behavior.sizeScale);
    const threatType = raw.threat_type || 'default';
    const haloColor =
      behavior.kind === 'fast' || behavior.kind === 'strike'
        ? '#ff3864'
        : behavior.kind === 'float'
          ? '#8bd3ff'
          : behavior.kind === 'watch'
            ? '#7ce7b2'
            : '#ff6b75';

    const rawCount = Number(raw.count) || 1;

    // Build tracker status label (ETA / Loitering)
    let statusLabel = '';
    // The user requested to remove all these labels ("оцінка", "прогноз", etc.)
    const isStale = raw.track_state === 'stale';

    // Ghost Mode styling override
    let finalHaloColor = haloColor;
    let finalOpacity = opacity;
    if (isStale) {
      finalHaloColor = '#9e9e9e'; // Grey halo
      finalOpacity = Math.min(opacity, 0.45); // Faded icon
    } else if (raw.last_observation_quality === 'target_hint') {
      finalHaloColor = '#f9b44e';
      finalOpacity = Math.min(opacity, 0.72);
    } else if (raw.last_observation_quality === 'coarse') {
      finalHaloColor = '#f6d96b';
      finalOpacity = Math.min(opacity, 0.78);
    } else if (raw.radar_state === 'coasting' || raw.radar_state === 'estimated') {
      finalHaloColor = '#8bd3ff';
      finalOpacity = Math.min(opacity, 0.82);
    }

    // Phase 4: Acoustic / Threat Zones
    let threatZoneRadiusKm = 0;
    if (threatType === 'shahed' || threatType === 'drone') {
      threatZoneRadiusKm = 8; // Acoustic zone for shaheds
    } else if (threatType === 'kab') {
      threatZoneRadiusKm = 10; // Impact zone for KABs
    } else if (threatType === 'missile' || threatType === 'raketa') {
      threatZoneRadiusKm = 6;
    }
    if (typeof raw.display_uncertainty_km === 'number' && raw.display_uncertainty_km > 0) {
      threatZoneRadiusKm = Math.max(threatZoneRadiusKm, Math.min(60, raw.display_uncertainty_km));
    }

    features.push({
      type: 'Feature',
      id: key,
      geometry: { type: 'Point', coordinates: [lng, lat] },
      properties: {
        mid: key,
        micon,
        bearing: rotation,
        opacity: finalOpacity,
        icon_px,
        halo_opacity: behavior.haloOpacity,
        halo_radius: behavior.haloRadiusPx,
        halo_color: finalHaloColor,
        behavior: behavior.kind,
        prio,
        threat_type: threatType,
        count: rawCount,
        count_label: '',
        badge_color: '',
        status_label: statusLabel,
        observation_quality: raw.last_observation_quality || '',
        text_intent: raw.last_text_intent || '',
        coordinate_role: raw.tracker_truth?.coordinate_role || '',
        public_position_policy: raw.tracker_truth?.public_position_policy || '',
        threat_zone_radius_km: threatZoneRadiusKm,
        /** серіалізація для popup */
        _m: JSON.stringify(raw),
      },
    });
  }

  return { type: 'FeatureCollection', features };
}

// ── Phase 3: Tactical Swarm Grouping (Convex Hulls) ──

function clusterMarkers(markers: Marker[], maxDistKm: number): Marker[][] {
  const clusters: Marker[][] = [];
  const visited = new Set<string>();

  for (const m of markers) {
    const id = m.id || m.track_id || Math.random().toString();
    if (visited.has(id)) continue;
    const cluster = [m];
    visited.add(id);
    
    const queue = [m];
    while (queue.length > 0) {
      const cur = queue.shift()!;
      for (const other of markers) {
        const oid = other.id || other.track_id || Math.random().toString();
        if (visited.has(oid)) continue;
        if (cur.threat_type !== other.threat_type) continue;
        
        const dLat = (Number(other.lat) - Number(cur.lat)) * 111.32;
        const dLng = (Number(other.lng) - Number(cur.lng)) * 111.32 * Math.cos(Number(cur.lat) * Math.PI / 180);
        const d = Math.sqrt(dLat * dLat + dLng * dLng);
        
        if (d <= maxDistKm) {
          visited.add(oid);
          cluster.push(other);
          queue.push(other);
        }
      }
    }
    clusters.push(cluster);
  }
  return clusters;
}

function convexHull(points: [number, number][]): [number, number][] {
  if (points.length < 3) return points;
  const p = [...points].sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const cross = (o: [number, number], a: [number, number], b: [number, number]) =>
    (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
  
  const lower: [number, number][] = [];
  for (const pt of p) {
    while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], pt) <= 0) lower.pop();
    lower.push(pt);
  }
  const upper: [number, number][] = [];
  for (let i = p.length - 1; i >= 0; i--) {
    const pt = p[i];
    while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], pt) <= 0) upper.pop();
    upper.push(pt);
  }
  upper.pop();
  lower.pop();
  const hull = lower.concat(upper);
  if (hull.length > 0) hull.push([...hull[0]]); // Close the polygon
  return hull;
}

export function markersToSwarmGeoJSON(markers: Marker[]) {
  const activeMarkers = markers.filter(m => markerPassesMapDisplayAge(normalizeMarkerDisplayForMap(m)) && m.track_state !== 'lost');
  const clusters = clusterMarkers(activeMarkers, 15.0); // 15 km cluster radius
  const features: any[] = [];

  for (const cluster of clusters) {
    if (cluster.length >= 3) {
      // Expand cluster points slightly so the hull isn't perfectly tight
      const points: [number, number][] = [];
      for (const m of cluster) {
        const lat = Number(m.lat);
        const lng = Number(m.lng);
        points.push([lng, lat]);
        // Add fake points around it to puff up the hull (creates a rounded buffer)
        points.push([lng + 0.02, lat]);
        points.push([lng - 0.02, lat]);
        points.push([lng, lat + 0.02]);
        points.push([lng, lat - 0.02]);
      }

      const hullCoords = convexHull(points);
      if (hullCoords.length < 4) continue;

      const threatType = cluster[0].threat_type || 'default';
      const label = `Зграя (${cluster.length})`;

      features.push({
        type: 'Feature',
        geometry: { type: 'Polygon', coordinates: [hullCoords] },
        properties: {
          swarm_id: `swarm_${cluster[0].id}`,
          threat_type: threatType,
          swarm_label: label,
        },
      });
    }
  }

  return { type: 'FeatureCollection', features };
}
