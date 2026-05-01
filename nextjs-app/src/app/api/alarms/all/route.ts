import { generateETag, withETag } from '@/lib/cache';
import { loadAlarms, withDevAllDistrictAlarms } from '@/lib/alarms-data';

/**
 * GET /api/alarms/all
 *
 * Reads alarms from Redis (populated by alarm-fetcher.ts every 10s).
 * Redis is shared between all Node.js contexts — no singleton issues.
 * Falls back to a single direct API fetch if Redis is empty (cold start).
 */

export async function GET(request: Request) {
  const clientETag = request.headers.get('If-None-Match');

  const loaded = await loadAlarms();

  if (loaded) {
    const data = withDevAllDistrictAlarms(loaded.data);
    const etag = data === loaded.data ? loaded.etag : generateETag(data);
    const headers: Record<string, string> = {
      'X-Data-Age': String(loaded.ageSeconds),
    };
    return withETag(data, etag, clientETag, headers);
  }

  return new Response(JSON.stringify(withDevAllDistrictAlarms([])), {
    status: 200,
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': 'public, max-age=3',
      'X-Data-Age': '-1',
    },
  });
}
