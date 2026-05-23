import type { FeatureCollection, Geometry } from 'geojson';
import type { ThreatMarker } from '../../../types/map';

export const EMPTY_FEATURE_COLLECTION: FeatureCollection = {
  type: 'FeatureCollection',
  features: [],
};

export function markersToFeatureCollection(markers: ThreatMarker[]): FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: markers.map((marker) => ({
      type: 'Feature',
      id: marker.id ?? marker.trackId ?? `${marker.lat},${marker.lng}`,
      geometry: {
        type: 'Point',
        coordinates: [marker.lng, marker.lat],
      },
      properties: {
        id: marker.id ?? '',
        trackId: marker.trackId ?? '',
        threatType: marker.threatType,
        text: marker.text,
        place: marker.place,
        count: marker.count ?? 1,
        bearing: marker.courseBearing ?? marker.tickerBearing ?? 0,
        confidence: marker.confidence0_100 ?? Math.round((marker.confidence ?? 0) * 100),
      },
    })),
  };
}

export function trajectoriesToFeatureCollection(markers: ThreatMarker[]): FeatureCollection<Geometry> {
  const features: FeatureCollection<Geometry>['features'] = [];
  for (const marker of markers) {
    if (marker.trajectory) {
      features.push({
        type: 'Feature',
        geometry: {
          type: 'LineString',
          coordinates: [
            [marker.trajectory.startLng, marker.trajectory.startLat],
            [marker.trajectory.endLng, marker.trajectory.endLat],
          ],
        },
        properties: { id: marker.id ?? marker.trackId ?? '', predicted: marker.trajectory.predicted },
      });
    }
    if (marker.positions && marker.positions.length > 1) {
      features.push({
        type: 'Feature',
        geometry: {
          type: 'LineString',
          coordinates: marker.positions.map((p) => [p.lng, p.lat]),
        },
        properties: { id: marker.id ?? marker.trackId ?? '', predicted: false },
      });
    }
  }
  return { type: 'FeatureCollection', features };
}
