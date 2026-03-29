import { NextResponse } from 'next/server';
import { getRedis } from '@/lib/redis';
import { requireAdminAuth } from '@/lib/admin/apiAuth';

const REDIS_FEED_KEY = 'admin:feed';

/**
 * GET /api/admin/feed
 * Returns the latest feed entries (newest first).
 * Auth: admin session cookie or X-Auth-Secret.
 *
 * Query params:
 *   limit  - max entries to return (default: 200, max: 500)
 *   offset - skip N entries (for pagination, default: 0)
 */
export async function GET(request: Request) {
  const authError = await requireAdminAuth();
  if (authError) return authError;

  const { searchParams } = new URL(request.url);
  const limit = Math.min(parseInt(searchParams.get('limit') || '200', 10) || 200, 500);
  const offset = parseInt(searchParams.get('offset') || '0', 10) || 0;

  try {
    const redis = getRedis();
    const raw = await redis.lrange(REDIS_FEED_KEY, offset, offset + limit - 1);
    const total = await redis.llen(REDIS_FEED_KEY);

    const entries = raw.map((item) => {
      try { return JSON.parse(item); } catch { return null; }
    }).filter(Boolean);

    return NextResponse.json({ entries, total, limit, offset });
  } catch (err) {
    console.warn('[FEED] Redis read error:', err);
    return NextResponse.json({ entries: [], total: 0, limit, offset });
  }
}
