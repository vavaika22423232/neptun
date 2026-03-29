import { withETag } from '@/lib/cache';
import { loadAlarms } from '@/lib/alarms-data';

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
    const headers: Record<string, string> = {
      'X-Data-Age': String(loaded.ageSeconds),
    };
    return withETag(loaded.data, loaded.etag, clientETag, headers, loaded.rawJson);
  }

  return new Response('[]', {
    status: 200,
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': 'public, max-age=3',
      'X-Data-Age': '-1',
    },
  });
}
