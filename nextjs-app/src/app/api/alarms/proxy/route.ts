import { withETag } from '@/lib/cache';
import { loadAlarms } from '@/lib/alarms-data';
import type { Alarm } from '@/types';

/**
 * GET /api/alarms/proxy
 *
 * Same data as /api/alarms/all, flattened for older mobile clients.
 */

function toProxyShape(data: Alarm[]) {
  return data
    .filter((r) => r.activeAlerts && r.activeAlerts.length > 0)
    .map((r) => ({
      regionId: r.regionId,
      regionType: r.regionType,
      regionName: r.regionName || '',
      type: r.activeAlerts![0]?.type || 'AIR',
      lastUpdate: r.activeAlerts![0]?.lastUpdate || '',
    }));
}

export async function GET(request: Request) {
  const clientETag = request.headers.get('If-None-Match');

  const loaded = await loadAlarms();

  if (!loaded || loaded.data.length === 0) {
    return new Response(JSON.stringify([]), {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'public, max-age=3',
        'X-Data-Age': '-1',
      },
    });
  }

  const proxyData = toProxyShape(loaded.data);
  const proxyETag = `"proxy-${loaded.etag.replace(/"/g, '')}"`;

  return withETag(proxyData, proxyETag, clientETag, {
    'X-Data-Age': String(loaded.ageSeconds),
  });
}
