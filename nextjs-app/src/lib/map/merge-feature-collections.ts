import type { FeatureCollection } from 'geojson';

export function mergeFeatureCollections(a: FeatureCollection, b: FeatureCollection): FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: [...(a.features ?? []), ...(b.features ?? [])],
  };
}
