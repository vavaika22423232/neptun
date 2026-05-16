import type { FeatureCollection } from 'geojson';
import { mergeFeatureCollections } from '@/lib/map/merge-feature-collections';

export async function fetchOccupiedTerritoriesMerged(cacheVersion: string): Promise<FeatureCollection> {
  const empty: FeatureCollection = { type: 'FeatureCollection', features: [] };
  const [adminRes, extraRes] = await Promise.all([
    fetch(`/ukraine_occupied_territories_admin.geojson?${cacheVersion}`, { cache: 'force-cache' }),
    fetch(`/ukraine_occupied_territories_extra.geojson?${cacheVersion}`, { cache: 'force-cache' }),
  ]);
  let admin = empty;
  let extra = empty;
  if (adminRes.ok) {
    try {
      admin = (await adminRes.json()) as FeatureCollection;
    } catch {
      /* malformed admin overlay */
    }
  }
  if (extraRes.ok) {
    try {
      extra = (await extraRes.json()) as FeatureCollection;
    } catch {
      /* malformed extra overlay */
    }
  }
  return mergeFeatureCollections(admin, extra);
}
