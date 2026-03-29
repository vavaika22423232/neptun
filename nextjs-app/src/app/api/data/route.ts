import { cache, withETag } from '@/lib/cache';
import type { Marker } from '@/types';
import { buildMarkers } from '@/lib/build-markers';
import { maybePrune, getLastIngestTime, getMarkersVersion, initStore } from '@/lib/markers-store';

const CACHE_KEY = 'data_markers';
const CACHE_KEY_EXTENDED = 'data_markers_extended';
const CACHE_TTL = 2_000; // 2 seconds — keep low for cross-worker consistency
const STALE_TTL = 300_000; // 5 minutes

export async function GET(request: Request) {
  const clientETag = request.headers.get('If-None-Match');

  await initStore();

  // timeRange>=60 — extended retention 180 min (3 год історії для шахедів/пусків)
  let extendedRange = false;
  try {
    const url = new URL(request.url);
    const timeRange = parseInt(url.searchParams.get('timeRange') || '15', 10);
    if (timeRange >= 60) extendedRange = true;
  } catch { /* use default */ }

  const cacheKey = extendedRange ? CACHE_KEY_EXTENDED : CACHE_KEY;

  // Background prune (in-memory, max once per minute)
  maybePrune();

  // Check cache
  const { entry, isStale } = cache.getWithStale<{
    tracks: Marker[];
    ballistic_threat: { active: boolean; region?: string; target?: string } | null;
    server_time: number;
    data_age: number | null;
    markers_version: number;
  }>(cacheKey, STALE_TTL);

  if (entry && !isStale) {
    const liveV = getMarkersVersion();
    if (entry.data.markers_version === liveV) {
      return withETag(entry.data, entry.etag, clientETag, {
        'X-NEPTUN-Marker-Count': String(entry.data.tracks.length),
        'X-NEPTUN-Markers-Version': String(entry.data.markers_version),
      }, entry.json);
    }
    cache.delete(cacheKey);
  }

  // Build from in-memory store (zero file I/O)
  const markers = buildMarkers({
    extendedRange,
    retentionMinutes: extendedRange ? 180 : undefined, // 3 год історії
  });

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const ballisticMarker = markers.find((m: any) =>
    m.threat_type === 'ballistic' || m.type === 'ballistic'
  );
  const ballistic_threat = ballisticMarker
    ? {
        active: true,
        region: (ballisticMarker as any).origin || ballisticMarker.place || undefined,
        target: (ballisticMarker as any).course_direction || ballisticMarker.place || undefined,
      }
    : null;

  const responseData = {
    tracks: markers,
    ballistic_threat,
    server_time: Date.now(),
    data_age: getLastIngestTime() > 0 ? Math.round((Date.now() - getLastIngestTime()) / 1000) : null,
    markers_version: getMarkersVersion(),
  };

  const newEntry = cache.set(cacheKey, responseData, CACHE_TTL);
  return withETag(newEntry.data, newEntry.etag, clientETag, {
    'X-NEPTUN-Marker-Count': String(markers.length),
    'X-NEPTUN-Markers-Version': String(responseData.markers_version),
  }, newEntry.json);
}
