/**
 * Threat trail GeoJSON builder — renders historical movement paths and projected vectors.
 *
 * Two feature types are produced:
 *  1. 'trail'      — LineString of observed positions (solid coloured line)
 *  2. 'projection' — Short LineString 1 step ahead using last bearing (dashed)
 */
import type { Marker } from '@/types';
import { destinationPoint } from '@/lib/marker-movement-policy';
import { resolveThreatBearingDeg } from '@/lib/threat-bearing';
import { trackMotionProfile } from '@/lib/track-motion-profile';

import { MAP_BOUNDS } from '@/lib/map/map-bounds';

type Position = [number, number]; // [lng, lat] for GeoJSON

function inBounds(lat: number, lng: number): boolean {
  return (
    lat >= MAP_BOUNDS.minLat && lat <= MAP_BOUNDS.maxLat &&
    lng >= MAP_BOUNDS.minLng && lng <= MAP_BOUNDS.maxLng
  );
}

/** Trail colour per threat type — matches the dimap.live palette */
export function trailColor(threatType: string): string {
  switch (threatType) {
    case 'ballistic': return '#dc143c';
    case 'missile':
    case 'raketa':
    case 'krylata':
    case 'pusk':    return '#ff2a5f';
    case 'kab':
    case 'rszv':    return '#ffd600';
    case 'rozved':
    case 'recon':   return '#4fc3f7';
    case 'fpv':     return '#f97316';
    default:        return '#ff6b35'; // shahed/drone/uav
  }
}

export type TrailFeature = {
  type: 'Feature';
  geometry: { type: 'LineString' | 'Point'; coordinates: any };
  properties: {
    mid: string;
    trail_kind: 'trail' | 'projection' | 'uncertainty' | 'checkpoint';
    threat_type: string;
    trail_color: string;
    trail_opacity: number;
    trail_width: number;
    checkpoint_label?: string;
  };
};

export type TrailFeatureCollection = {
  type: 'FeatureCollection';
  features: TrailFeature[];
};

const STATIC_TYPES = new Set([
  'explosion', 'vibuh', 'alert', 'allclear', 'chemical', 'nuclear', 'artillery', 'obstril', 'info',
]);

/** Min 2 points separated by > 0.3 km for a trail to be worthwhile */
function significantTrail(coords: Position[]): boolean {
  if (coords.length < 2) return false;
  let totalDist = 0;
  for (let i = 1; i < coords.length; i++) {
    const [aLng, aLat] = coords[i - 1]!;
    const [bLng, bLat] = coords[i]!;
    const dLat = (bLat - aLat) * 111.32;
    const dLng = (bLng - aLng) * 111.32 * Math.cos(aLat * Math.PI / 180);
    totalDist += Math.sqrt(dLat * dLat + dLng * dLng);
    if (totalDist > 0.3) return true;
  }
  return false;
}

export function markersToTrailsGeoJSON(markers: Marker[]): TrailFeatureCollection {
  const features: TrailFeature[] = [];

  for (const m of markers) {
    const threatType = (m.threat_type || 'default').toLowerCase();
    if (STATIC_TYPES.has(threatType)) continue;

    const trackState = String(m.track_state || 'observed');
    if (trackState === 'lost') continue;

    // Build observation list from observations[], positions[], or trajectory waypoints
    const rawObs = (m.observations as Array<{ lat: number; lng: number; ts?: number }> | undefined) ||
      (m.positions as Array<{ lat: number; lng: number; ts?: number }> | undefined);

    const trailCoords: Position[] = [];

    if (rawObs && rawObs.length >= 2) {
      for (const pt of rawObs) {
        const lat = Number(pt.lat);
        const lng = Number(pt.lng);
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) continue;
        if (!inBounds(lat, lng)) continue;
        trailCoords.push([lng, lat]);
      }
    } else if (m.trajectory?.start && m.trajectory?.end) {
      // Fallback: use trajectory start→current as trail
      const [sLat, sLng] = m.trajectory.start as [number, number];
      const lat = Number(m.lat);
      const lng = Number(m.lng);
      if (inBounds(sLat, sLng) && inBounds(lat, lng)) {
        trailCoords.push([sLng, sLat], [lng, lat]);
      }
    }

    // Add current position as last trail point if not already there
    const curLat = Number(m.lat);
    const curLng = Number(m.lng);
    if (
      Number.isFinite(curLat) && Number.isFinite(curLng) && inBounds(curLat, curLng) &&
      trailCoords.length > 0
    ) {
      const last = trailCoords[trailCoords.length - 1]!;
      if (Math.abs(last[0] - curLng) > 0.001 || Math.abs(last[1] - curLat) > 0.001) {
        trailCoords.push([curLng, curLat]);
      }
    }

    const mid = m.track_id ? `t:${m.track_id}` : m.id ? `i:${m.id}` : `p:${curLat.toFixed(3)}_${curLng.toFixed(3)}`;
    const color = trailColor(threatType);
    const trailOpacity = trackState === 'extrapolated' ? 0.45 : trackState === 'stale' ? 0.25 : 0.65;
    const trailWidth = threatType === 'ballistic' ? 2.5 : 1.8;

    if (significantTrail(trailCoords)) {
      features.push({
        type: 'Feature',
        geometry: { type: 'LineString', coordinates: trailCoords },
        properties: {
          mid,
          trail_kind: 'trail',
          threat_type: threatType,
          trail_color: color,
          trail_opacity: trailOpacity,
          trail_width: trailWidth,
        },
      });
    }

    // ── Projection Line or Loitering Zone ──
    // ── Phase 2: Uncertainty Rings (Ghost Mode) ──
    if (trackState === 'stale') {
      const ageMs = Number(m.age_ms) || 5 * 60_000;
      const currentSpeedKmh = Number(m.speed_kmh) || Number(m.computed_speed_kmh) || 170;
      const hoursLost = Math.min(ageMs / 3_600_000, 2); // Max 2 hours 
      const uncertaintyRadiusKm = Math.max(currentSpeedKmh * hoursLost, 5.0);

      const circleCoords: Position[] = [];
      for (let i = 0; i <= 36; i++) {
        const angle = i * 10;
        const [cLat, cLng] = destinationPoint(curLat, curLng, angle, uncertaintyRadiusKm);
        circleCoords.push([cLng, cLat]);
      }
      features.push({
        type: 'Feature',
        geometry: { type: 'LineString', coordinates: circleCoords },
        properties: {
          mid: `${mid}_uncertainty`,
          trail_kind: 'uncertainty',
          threat_type: threatType,
          trail_color: '#9e9e9e', // Grey dashed ring
          trail_opacity: 0.6,
          trail_width: 1.5,
        },
      });
      continue;
    }

    if (trackState === 'lost') continue;
    if (!Number.isFinite(curLat) || !Number.isFinite(curLng)) continue;

    // If loitering, draw a dashed circle (Loitering Zone) instead of a straight line
    if (m.is_loitering) {
      const circleCoords: Position[] = [];
      const radiusKm = 4.0; // 4 km loitering radius
      for (let i = 0; i <= 36; i++) {
        const angle = i * 10;
        const [cLat, cLng] = destinationPoint(curLat, curLng, angle, radiusKm);
        circleCoords.push([cLng, cLat]);
      }
      features.push({
        type: 'Feature',
        geometry: { type: 'LineString', coordinates: circleCoords },
        properties: {
          mid: `${mid}_loiter`,
          trail_kind: 'projection',
          threat_type: threatType,
          trail_color: color,
          trail_opacity: 0.5,
          trail_width: 2.0,
        },
      });
      continue;
    }

    const bearingDeg = resolveThreatBearingDeg(m);
    if (bearingDeg == null) continue;

    const profile = trackMotionProfile(threatType);
    let projDistKm: number;
    
    // Dynamically scale the vector line to the exact AI-calculated ETA target
    if (typeof m.eta_seconds === 'number' && m.eta_seconds > 0) {
      // Cap at 25 mins so the line doesn't span across the whole country
      const projectionSeconds = Math.min(m.eta_seconds, 25 * 60);
      const currentSpeedKmh = Number(m.speed_kmh) || Number(m.computed_speed_kmh) || profile.nominalSpeedKmh;
      projDistKm = currentSpeedKmh * (projectionSeconds / 3600);
      
      // Ensure minimum length so it's always visible as a pointer
      if (projDistKm < 2.0) projDistKm = 2.0; 
    } else {
      // Fallback: 8 minutes ahead
      projDistKm = profile.nominalSpeedKmh * (8 / 60);
    }

    const [pLat, pLng] = destinationPoint(curLat, curLng, bearingDeg, projDistKm);

    if (inBounds(pLat, pLng)) {
      features.push({
        type: 'Feature',
        geometry: {
          type: 'LineString',
          coordinates: [[curLng, curLat], [pLng, pLat]],
        },
        properties: {
          mid: `${mid}_proj`,
          trail_kind: 'projection',
          threat_type: threatType,
          trail_color: color,
          trail_opacity: typeof m.eta_seconds === 'number' ? 0.6 : 0.4, // Brighter if AI targeted
          trail_width: 1.5,
        },
      });

      // ── ETA Checkpoints ──
      const currentSpeedKmh = Number(m.speed_kmh) || Number(m.computed_speed_kmh) || profile.nominalSpeedKmh;
      const checkpointIntervalMins = 5;
      const totalMins = typeof m.eta_seconds === 'number' && m.eta_seconds > 0 
          ? Math.min(m.eta_seconds / 60, 25) 
          : 8;
          
      for (let min = checkpointIntervalMins; min <= totalMins - 1; min += checkpointIntervalMins) {
        const cpDistKm = currentSpeedKmh * (min / 60);
        const [cpLat, cpLng] = destinationPoint(curLat, curLng, bearingDeg, cpDistKm);
        if (inBounds(cpLat, cpLng)) {
          features.push({
            type: 'Feature',
            geometry: { type: 'Point', coordinates: [cpLng, cpLat] },
            properties: {
              mid: `${mid}_cp_${min}`,
              trail_kind: 'checkpoint',
              threat_type: threatType,
              trail_color: color,
              checkpoint_label: `+${min}хв`,
              trail_opacity: 0,
              trail_width: 0,
            },
          });
        }
      }
    }
  }

  return { type: 'FeatureCollection', features };
}
