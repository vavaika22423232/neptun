import { getRedis } from '@/lib/redis';

/**
 * Fixed-window counter in Redis (cluster-safe). Returns false if over limit.
 * `failOpen` controls behavior on Redis errors:
 *   - true  (default): allows the request if Redis is down (suitable for non-sensitive endpoints)
 *   - false: rejects the request on Redis errors (use for auth, admin, ingest)
 */
export async function redisFixedWindowAllow(
  key: string,
  limit: number,
  windowSec: number,
  failOpen = true,
): Promise<boolean> {
  try {
    const r = getRedis();
    const n = await r.incr(key);
    if (n === 1) await r.expire(key, windowSec);
    return n <= limit;
  } catch {
    return failOpen;
  }
}
