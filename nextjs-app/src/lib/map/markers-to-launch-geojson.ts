import type { FeatureCollection, Feature, LineString, Point } from 'geojson';
import type { Marker } from '@/types';
import { resolveLaunchSite } from '@/lib/map/launch-sites';

export interface LaunchArcFeatureProperties {
  track_id: string;
  threat_type: string;
  origin_name: string;
  opacity: number;
}

export interface LaunchSiteFeatureProperties {
  name: string;
  shortName: string;
  count: number;
  opacity: number;
}

/**
 * Generates a Bezier-curve arc from launch origin to target marker.
 * The control point is offset perpendicular to the line for a natural bow.
 */
function makeBezierArc(
  originLng: number, originLat: number,
  targetLng: number, targetLat: number,
  steps = 32,
): [number, number][] {
  // Control point: midpoint offset perpendicular to the line
  const midLng = (originLng + targetLng) / 2;
  const midLat = (originLat + targetLat) / 2;

  // Perpendicular offset — scale with distance
  const dx = targetLng - originLng;
  const dy = targetLat - originLat;
  const dist = Math.sqrt(dx * dx + dy * dy);
  const offsetScale = Math.min(dist * 0.25, 4); // max 4 degrees offset

  // Rotate 90° for perpendicular
  const cpLng = midLng - (dy / dist) * offsetScale;
  const cpLat = midLat + (dx / dist) * offsetScale;

  const coords: [number, number][] = [];
  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    const mt = 1 - t;
    const lng = mt * mt * originLng + 2 * mt * t * cpLng + t * t * targetLng;
    const lat = mt * mt * originLat + 2 * mt * t * cpLat + t * t * targetLat;
    coords.push([lng, lat]);
  }
  return coords;
}

/**
 * Build GeoJSON FeatureCollections for:
 *  - Arc lines from launch origin to current marker position
 *  - Launch site point markers
 */
export function markersToLaunchGeoJSON(markers: Marker[]): {
  arcs: FeatureCollection<LineString, LaunchArcFeatureProperties>;
  sites: FeatureCollection<Point, LaunchSiteFeatureProperties>;
} {
  const arcFeatures: Feature<LineString, LaunchArcFeatureProperties>[] = [];
  const siteMap = new Map<string, { site: ReturnType<typeof resolveLaunchSite>; count: number }>();

  for (const marker of markers) {
    if (!marker.origin) continue;
    const site = resolveLaunchSite(marker.origin);
    if (!site) continue;

    const targetLat = marker.lat;
    const targetLng = marker.lng;

    // Don't draw arcs to invalid positions
    if (!targetLat || !targetLng) continue;
    if (Math.abs(targetLat) < 1 || Math.abs(targetLng) < 1) continue;

    // Opacity based on track_state
    const state = marker.track_state || 'observed';
    const opacity = state === 'stale' ? 0.25 : state === 'lost' ? 0.1 : 0.55;

    // Arc from origin to target
    const coords = makeBezierArc(site.lng, site.lat, targetLng, targetLat);
    arcFeatures.push({
      type: 'Feature',
      geometry: { type: 'LineString', coordinates: coords },
      properties: {
        track_id: marker.track_id || marker.id || '',
        threat_type: marker.threat_type || 'shahed',
        origin_name: site.name,
        opacity,
      },
    });

    // Accumulate site points
    const key = site.name;
    const existing = siteMap.get(key);
    if (existing) {
      existing.count++;
    } else {
      siteMap.set(key, { site, count: 1 });
    }
  }

  const siteFeatures: Feature<Point, LaunchSiteFeatureProperties>[] = [];
  for (const [, { site, count }] of siteMap) {
    if (!site) continue;
    siteFeatures.push({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [site.lng, site.lat] },
      properties: {
        name: site.name,
        shortName: site.shortName,
        count,
        opacity: Math.min(0.9, 0.5 + count * 0.1),
      },
    });
  }

  return {
    arcs: { type: 'FeatureCollection', features: arcFeatures },
    sites: { type: 'FeatureCollection', features: siteFeatures },
  };
}
