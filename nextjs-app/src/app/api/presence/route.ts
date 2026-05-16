import { NextResponse } from 'next/server';
import { getRedis } from '@/lib/redis';

/**
 * Presence tracking via Redis sorted sets (cluster-safe).
 *
 * Two sorted sets: presence:web and presence:app
 * Score = Unix timestamp (ms), member = user ID.
 * Users with score older than VISITOR_TIMEOUT are expired via ZREMRANGEBYSCORE.
 */

// Must exceed client POST heartbeat interval (PRESENCE_INTERVAL) so users are not dropped between pings.
const VISITOR_TIMEOUT = 420_000; // 7 minutes
const KEY_WEB = 'presence:web';
const KEY_APP = 'presence:app';

/** Легке читання лічильників без ZADD — для HUD-полінгу клієнта кожні кілька секунд. */
export async function GET() {
  try {
    const redis = getRedis();
    const now = Date.now();
    const cutoff = now - VISITOR_TIMEOUT;
    const pipe = redis.pipeline();
    pipe.zremrangebyscore(KEY_WEB, 0, cutoff);
    pipe.zremrangebyscore(KEY_APP, 0, cutoff);
    pipe.zcard(KEY_WEB);
    pipe.zcard(KEY_APP);
    const results = await pipe.exec();
    const web = (results?.[2]?.[1] as number) || 0;
    const apps = (results?.[3]?.[1] as number) || 0;
    return NextResponse.json({
      total: web + apps,
      web,
      apps,
      android: apps,
    });
  } catch (err) {
    console.warn('[PRESENCE] GET Redis error:', err);
    return NextResponse.json({ total: 0, web: 0, apps: 0 }, { status: 200 });
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { id, platform } = body;

    if (!id) {
      return NextResponse.json({ error: 'Missing id' }, { status: 400 });
    }

    const redis = getRedis();
    const now = Date.now();
    const cutoff = now - VISITOR_TIMEOUT;
    const isWeb = (platform || 'web') === 'web';
    const key = isWeb ? KEY_WEB : KEY_APP;

    // Pipeline: add user + cleanup expired + count both sets
    const pipe = redis.pipeline();
    pipe.zadd(key, now, id);            // upsert this user
    pipe.zremrangebyscore(KEY_WEB, 0, cutoff);  // expire old web
    pipe.zremrangebyscore(KEY_APP, 0, cutoff);  // expire old app
    pipe.zcard(KEY_WEB);                // count web
    pipe.zcard(KEY_APP);                // count app
    const results = await pipe.exec();

    const web = (results?.[3]?.[1] as number) || 0;
    const apps = (results?.[4]?.[1] as number) || 0;

    return NextResponse.json({
      total: web + apps,
      web,
      apps,
      android: apps,
    });
  } catch (err) {
    console.warn('[PRESENCE] Redis error:', err);
    return NextResponse.json({ total: 0, web: 0, apps: 0 }, { status: 200 });
  }
}
