import { NextResponse } from 'next/server';
import { getClientIp, ipRedisTag } from '@/lib/client-ip';
import {
  isSettlementsDbAvailable,
  popularPlaces,
  searchPlaces,
} from '@/lib/places-search/db';
import type { PlaceSearchResponse } from '@/lib/places-search/types';
import { redisFixedWindowAllow } from '@/lib/redis-rate-limit';

export const dynamic = 'force-dynamic';

const RATE_LIMIT = 30;
const RATE_WINDOW_SEC = 60;

const rateBuckets = new Map<string, { count: number; resetAt: number }>();

function inMemoryRateLimit(ip: string): boolean {
  const now = Date.now();
  const key = ipRedisTag(ip);
  let bucket = rateBuckets.get(key);
  if (!bucket || bucket.resetAt <= now) {
    bucket = { count: 0, resetAt: now + RATE_WINDOW_SEC * 1000 };
    rateBuckets.set(key, bucket);
  }
  bucket.count += 1;
  if (rateBuckets.size > 5000) {
    for (const [k, v] of rateBuckets) {
      if (v.resetAt <= now) rateBuckets.delete(k);
    }
  }
  return bucket.count <= RATE_LIMIT;
}

export async function GET(request: Request) {
  const ip = getClientIp(request);
  const redisOk = await redisFixedWindowAllow(
    `rl:places:search:${ipRedisTag(ip)}`,
    RATE_LIMIT,
    RATE_WINDOW_SEC,
    true,
  );
  if (!redisOk && !inMemoryRateLimit(ip)) {
    return NextResponse.json({ error: 'Too many requests' }, { status: 429 });
  }

  const url = new URL(request.url);
  const q = (url.searchParams.get('q') || '').trim();
  const popular = url.searchParams.get('popular') === '1';
  const limitRaw = Number.parseInt(url.searchParams.get('limit') || '8', 10);
  const limit = Math.max(1, Math.min(20, Number.isFinite(limitRaw) ? limitRaw : 8));
  const typeFilter = url.searchParams.get('type')?.trim() || undefined;
  const validTypes = new Set(['city', 'town', 'village', 'suburb', 'other']);
  const type = typeFilter && validTypes.has(typeFilter) ? typeFilter : undefined;

  if (popular && q.length === 0) {
    const body: PlaceSearchResponse = { results: popularPlaces() };
    return NextResponse.json(body, {
      headers: { 'Cache-Control': 'public, max-age=300' },
    });
  }

  if (q.length < 2) {
    return NextResponse.json({ results: [] } satisfies PlaceSearchResponse);
  }

  const results = searchPlaces(q, limit, type);
  if (!results.length && !isSettlementsDbAvailable()) {
    return NextResponse.json(
      { error: 'Place search temporarily unavailable', results: [] },
      { status: 503 },
    );
  }
  const body: PlaceSearchResponse = { results };

  return NextResponse.json(body, {
    headers: {
      'Cache-Control': 'public, max-age=3600, stale-while-revalidate=600',
    },
  });
}
