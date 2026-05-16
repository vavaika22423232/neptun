import { NextResponse } from 'next/server';
import { getRedis } from '@/lib/redis';
import { broadcastSSE } from '@/lib/chat-sse-stream';
import { verifyIngestOrRespond } from '@/lib/ingest-auth-guard';
import { normalizeMaritimeFeedEvent } from '@/lib/feed-maritime-normalize';

const REDIS_FEED_KEY = 'admin:feed';
const REDIS_FEED_MSG_META_PREFIX = 'admin:feed:msgmeta:';
const MAX_FEED_ENTRIES = 500;
const FEED_TTL_SECONDS = 3 * 3600; // 3 hours
const DEDUP_WINDOW_SECONDS = 120; // last-wins merge for same Telegram message

function msgMetaKey(channelId: number, messageId: number): string {
  return `${REDIS_FEED_MSG_META_PREFIX}${channelId}:${messageId}`;
}

/**
 * POST /api/admin/feed/ingest
 * Called by the Python worker to push pipeline events into the admin feed.
 * Auth: X-Auth-Secret header (same as ingest).
 *
 * How feed rows relate to the public map: see `docs/JOURNAL_STATUS_TO_PUBLIC_MAP.md`.
 * Allclear vs markers: see `docs/ALLCLEAR_AND_PUBLIC_MAP.md`.
 *
 * Body: { event: FeedEvent }
 *
 * FeedEvent shape:
 * {
 *   ts: string,             // ISO timestamp
 *   status: 'processed' | 'skipped' | 'deduped' | 'dropped' | 'error' | 'chain_update',
 *   reason?: string,        // why skipped/dropped/error
 *   channel_name: string,
 *   channel_id?: number,
 *   msg_id?: number,
 *   msg_text: string,       // truncated (max 300 chars)
 *   threat_type?: string,
 *   entities_count?: number,
 *   parser?: 'gpt' | 'regex' | 'both_empty',
 *   place?: string,
 *   region?: string,
 *   context_region?: string, // optional: oblast context for maritime/offshore (set server-side)
 *   lat?: number,
 *   lng?: number,
 *   speed_kmh?: number,
 *   course_bearing?: number,
 *   track_id?: string,
 *   confidence?: number,
 *   resolve_status?: string,
 *   marker_id?: string,
 *   origin?: string,
 *   impact_place?: string, // KAB impact label when `place` is the synthetic airfield (phantom avia)
 * }
 */
export async function POST(request: Request) {
  const denied = await verifyIngestOrRespond(request);
  if (denied) return denied;

  let body: { event?: Record<string, unknown> };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 });
  }

  const event = body.event;
  if (!event || !event.status || !event.channel_name) {
    return NextResponse.json({ error: 'Missing event or required fields' }, { status: 400 });
  }

  normalizeMaritimeFeedEvent(event);

  // Add server-side ID
  event._id = `feed_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;

  try {
    const redis = getRedis();
    const now = Date.now() / 1000;
    const chId =
      typeof event.channel_id === 'number' && Number.isFinite(event.channel_id)
        ? event.channel_id
        : 0;
    const msgId =
      typeof event.msg_id === 'number' && Number.isFinite(event.msg_id) ? event.msg_id : 0;
    const json = JSON.stringify(event);

    // ── Last-wins dedup: one visible row per (channel_id, msg_id) within window ──
    if (chId && msgId) {
      const mkey = msgMetaKey(chId, msgId);
      const prevRaw = await redis.get(mkey);
      if (prevRaw) {
        try {
          const prev = JSON.parse(prevRaw) as { t?: number; payload?: string };
          const prevT = typeof prev.t === 'number' ? prev.t : 0;
          const payload = typeof prev.payload === 'string' ? prev.payload : '';
          if (payload && now - prevT < DEDUP_WINDOW_SECONDS) {
            await redis.lrem(REDIS_FEED_KEY, 1, payload);
          }
        } catch {
          /* ignore bad meta */
        }
      }
      await redis.set(mkey, JSON.stringify({ t: now, payload: json }), 'EX', FEED_TTL_SECONDS);
    }

    const pipeline = redis.pipeline();
    pipeline.lpush(REDIS_FEED_KEY, json);
    pipeline.ltrim(REDIS_FEED_KEY, 0, MAX_FEED_ENTRIES - 1);
    pipeline.expire(REDIS_FEED_KEY, FEED_TTL_SECONDS);
    await pipeline.exec();

    broadcastSSE({ type: 'admin_feed', data: event });
  } catch (err) {
    console.warn('[FEED] Redis write error:', err);
    return NextResponse.json({ error: 'Storage error' }, { status: 500 });
  }

  return NextResponse.json({ ok: true });
}
