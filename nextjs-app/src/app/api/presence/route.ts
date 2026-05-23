import { NextResponse } from 'next/server';
import { PRESENCE_VISITOR_TIMEOUT_MS } from '@/lib/constants';
import { getRedis } from '@/lib/redis';
import { PresencePingSchema } from '@/lib/api-schemas';
import { getClientIp, ipRedisTag } from '@/lib/client-ip';
import { redisFixedWindowAllow } from '@/lib/redis-rate-limit';
import { logSecurityEvent } from '@/lib/security-log';

/**
 * Presence tracking via Redis sorted sets (cluster-safe).
 *
 * Two sorted sets: presence:web and presence:app
 * Score = Unix timestamp (ms), member = user ID.
 * Users with score older than VISITOR_TIMEOUT are expired via ZREMRANGEBYSCORE.
 *
 * «Онлайн» = активна сесія (вкладка/додаток відкриті), у т.ч. у фоні — не лише активний перегляд.
 */

const VISITOR_TIMEOUT = PRESENCE_VISITOR_TIMEOUT_MS;
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
    const ip = getClientIp(request);
    const allowed = await redisFixedWindowAllow(
      `rl:presence:${ipRedisTag(ip)}`,
      120,
      60,
      false,
    );
    if (!allowed) {
      logSecurityEvent('rate_limit_hit', { route: 'presence_post' });
      return NextResponse.json({ error: 'rate_limited' }, { status: 429 });
    }

    const parsed = PresencePingSchema.safeParse(await request.json());
    if (!parsed.success) {
      return NextResponse.json({ error: 'Invalid input' }, { status: 400 });
    }

    const { id, platform } = parsed.data;

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
