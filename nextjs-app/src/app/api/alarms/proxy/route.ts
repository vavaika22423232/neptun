import { cache, withETag } from '@/lib/cache';
import type { Alarm } from '@/types';

const CACHE_KEY = 'alarms_all';
const STALE_TTL = 7200_000; // 2 hours

/**
 * Proxy endpoint for alarms - serves from the same cache as /api/alarms/all
 * but reformats the data for mobile clients.
 */
export async function GET(request: Request) {
  const clientETag = request.headers.get('If-None-Match');

  // Try cache first
  const { entry } = cache.getWithStale<Alarm[]>(CACHE_KEY, STALE_TTL);

  if (entry) {
    // Transform to proxy format (flattened)
    const proxyData = entry.data
      .filter((r) => r.activeAlerts && r.activeAlerts.length > 0)
      .map((r) => ({
        regionId: r.regionId,
        regionType: r.regionType,
        regionName: r.regionName || '',
        type: r.activeAlerts[0]?.type || 'AIR',
        lastUpdate: r.activeAlerts[0]?.lastUpdate || '',
      }));

    const proxyETag = `"proxy-${entry.etag.replace(/"/g, '')}"`;
    return withETag(proxyData, proxyETag, clientETag);
  }

  // No cache - redirect client to /api/alarms/all
  return new Response(JSON.stringify([]), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
}
