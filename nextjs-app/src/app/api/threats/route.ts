import { cache, withETag } from '@/lib/cache';
import type { Marker } from '@/types';
import { buildMarkers, buildMarkerOptionsForApi } from '@/lib/build-markers';
import { getMarkersVersion, initStore } from '@/lib/markers-store';

const THREATS_CACHE_KEY = 'threats_data';
const THREATS_CACHE_KEY_EXTENDED = 'threats_data_extended';
const CACHE_TTL = 5_000; // 5 seconds
const STALE_TTL = 300_000; // 5 minutes

function buildThreats(options?: { extendedRange?: boolean; retentionMinutes?: number }): {
  status: 'ok';
  total: number;
  counts: Record<string, number>;
  summary: Record<string, number>;
  threats: Array<{
    id: string;
    type?: string;
    place: string;
    region: string;
    text: string;
    date: string;
    description: string;
    course_direction: string;
    speed_kmh?: number;
    lat?: number;
    lng?: number;
    track_id?: string;
    course_bearing?: number;
  }>;
  updated_at: string;
  markers_version: number;
} {
  // Read markers directly from markers-store (no dependency on /api/data cache)
  const markers = buildMarkers(options);

  // Count threats by type
  const counts: Record<string, number> = {};
  markers.forEach((m) => {
    const type = m.threat_type || 'unknown';
    counts[type] = (counts[type] || 0) + 1;
  });

  // Summary grouped by category (matches Flutter expectations)
  const summary = {
    drones: (counts.shahed || 0) + (counts.drone || 0) + (counts.uav || 0) + (counts.fpv || 0),
    missiles: (counts.raketa || 0) + (counts.missile || 0),
    kab: (counts.kab || 0) + (counts.rszv || 0),
    ballistic: (counts.ballistic || 0) + (counts.pusk || 0) + (counts.launch || 0),
    avia: counts.avia || 0,
  };

  // Individual threats as array (sorted newest first)
  const threats = markers
    .map((m) => {
      const lat = typeof m.lat === 'number' ? m.lat : undefined;
      const lng = typeof m.lng === 'number' ? m.lng : undefined;
      const rawText = m.text || '';
      const trimmed = rawText.length > 500 ? rawText.slice(0, 500) : rawText;
      return {
        id: (m.id ?? m.track_id ?? '') as string,
        type: m.threat_type,
        place: m.place || m.region || '',
        region: m.region || '',
        text: trimmed,
        date: m.date || '',
        description: trimmed,
        course_direction: m.course_direction || '',
        speed_kmh: m.speed_kmh,
        ...(lat != null && lng != null ? { lat, lng } : {}),
        ...(m.track_id ? { track_id: m.track_id } : {}),
        ...(typeof m.course_bearing === 'number' ? { course_bearing: m.course_bearing } : {}),
      };
    })
    .sort((a, b) => {
      const da = a.date ? new Date(a.date).getTime() : 0;
      const db = b.date ? new Date(b.date).getTime() : 0;
      return db - da;
    });

  return {
    status: 'ok' as const,
    total: markers.length,
    counts,
    summary,
    threats,
    updated_at: new Date().toISOString(),
    markers_version: getMarkersVersion(),
  };
}

export async function GET(request: Request) {
  const clientETag = request.headers.get('If-None-Match');

  // timeRange>=60 — same retention policy as /api/data (admin monitorPeriod)
  let extendedRange = false;
  try {
    const url = new URL(request.url);
    const timeRange = parseInt(url.searchParams.get('timeRange') || '15', 10);
    if (timeRange >= 60) extendedRange = true;
  } catch { /* use default */ }

  const cacheKey = extendedRange ? THREATS_CACHE_KEY_EXTENDED : THREATS_CACHE_KEY;

  await initStore();

  // Check cache
  const { entry, isStale } = cache.getWithStale<ReturnType<typeof buildThreats>>(cacheKey, STALE_TTL);

  if (entry && !isStale) {
    const liveV = getMarkersVersion();
    if (entry.data.markers_version === liveV) {
      return withETag(entry.data, entry.etag, clientETag, undefined, entry.json);
    }
    cache.delete(cacheKey);
  }

  // Rebuild (reads from in-memory markers cache)
  const data = buildThreats(buildMarkerOptionsForApi(extendedRange));
  const newEntry = cache.set(cacheKey, data, CACHE_TTL);
  return withETag(newEntry.data, newEntry.etag, clientETag, undefined, newEntry.json);
}
