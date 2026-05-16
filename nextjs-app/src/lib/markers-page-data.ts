/**
 * Server-side public markers snapshot for the map homepage (matches GET /api/data?timeRange>=60).
 * Lets the client hydrate with markers immediately instead of waiting for the first client fetch.
 */
import type { Marker, BallisticThreat } from '@/types';
import { buildMarkers, buildMarkerOptionsForApi } from '@/lib/build-markers';
import { initTargetStore, syncTargetStoreFromRedis, getTrackedTargetsVersion } from '@/lib/tracked-target-store';

export type InitialPublicMarkersPayload = {
  markers: Marker[];
  markersVersion: number;
  serverTime: number;
  ballisticThreat: BallisticThreat | null;
};

function deriveBallisticThreat(markers: Marker[]): BallisticThreat | null {
  const ballisticMarker = markers.find((m) => m.threat_type === 'ballistic' || m.type === 'ballistic');
  if (!ballisticMarker) return null;
  return {
    active: true,
    region: ballisticMarker.origin || ballisticMarker.place || undefined,
    target: ballisticMarker.course_direction || ballisticMarker.place || undefined,
  };
}

export async function getInitialPublicMarkersPayload(): Promise<InitialPublicMarkersPayload> {
  await initTargetStore();
  await syncTargetStoreFromRedis();
  const markers = buildMarkers(buildMarkerOptionsForApi(true));
  return {
    markers,
    markersVersion: getTrackedTargetsVersion(),
    serverTime: Date.now(),
    ballisticThreat: deriveBallisticThreat(markers),
  };
}
