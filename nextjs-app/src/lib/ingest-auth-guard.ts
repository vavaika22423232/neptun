import { NextResponse } from 'next/server';
import { getRedis } from '@/lib/redis';
import { getIngestSecret, safeCompare } from '@/lib/server-secrets';
import { getClientIp, ipRedisTag } from '@/lib/client-ip';

/** Failed X-Auth-Secret attempts per IP before temporary block. */
const MAX_INGEST_AUTH_FAILURES = 35;
const FAILURE_WINDOW_SEC = 900; // 15 minutes

const disabled = () => process.env.DISABLE_INGEST_BRUTE_GUARD === '1';

function failKey(ipTag: string): string {
  return `ingest:authfail:${ipTag}`;
}

async function isIngestLockedOut(ipTag: string): Promise<boolean> {
  if (disabled()) return false;
  try {
    const raw = await getRedis().get(failKey(ipTag));
    const n = raw ? parseInt(raw, 10) : 0;
    return Number.isFinite(n) && n >= MAX_INGEST_AUTH_FAILURES;
  } catch {
    return false;
  }
}

async function recordIngestAuthFailure(ipTag: string): Promise<void> {
  if (disabled()) return;
  try {
    const r = getRedis();
    const k = failKey(ipTag);
    const n = await r.incr(k);
    if (n === 1) await r.expire(k, FAILURE_WINDOW_SEC);
  } catch {
    /* ignore */
  }
}

async function clearIngestAuthFailures(ipTag: string): Promise<void> {
  try {
    await getRedis().del(failKey(ipTag));
  } catch {
    /* ignore */
  }
}

/**
 * Validates ingest secret and applies Redis-backed lockout after repeated wrong secrets.
 * Returns null if the request may proceed, otherwise a finished NextResponse (401/429/500).
 */
export async function verifyIngestOrRespond(request: Request): Promise<NextResponse | null> {
  const ingestSecret = getIngestSecret();
  if (!ingestSecret) {
    return NextResponse.json({ error: 'Ingest secret not configured' }, { status: 500 });
  }

  const ipTag = ipRedisTag(getClientIp(request));
  if (await isIngestLockedOut(ipTag)) {
    return NextResponse.json(
      { error: 'Too many failed authentication attempts. Try again later.' },
      { status: 429 },
    );
  }

  const authHeader = request.headers.get('X-Auth-Secret') || '';
  if (!authHeader || !safeCompare(authHeader, ingestSecret)) {
    await recordIngestAuthFailure(ipTag);
    console.warn(`[INGEST] 401 Unauthorized (ip tag ${ipTag.slice(0, 8)}…)`);
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  await clearIngestAuthFailures(ipTag);
  return null;
}
