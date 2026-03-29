import { NextResponse } from 'next/server';
import { getRedis } from '@/lib/redis';
import { broadcastSSE } from '@/app/api/chat/stream/route';
import { verifyIngestOrRespond } from '@/lib/ingest-auth-guard';

const REDIS_FEED_KEY = 'admin:feed';
const MAX_FEED_ENTRIES = 500;
const FEED_TTL_SECONDS = 3 * 3600; // 3 hours

/**
 * POST /api/admin/feed/ingest
 * Called by the Python worker to push pipeline events into the admin feed.
 * Auth: X-Auth-Secret header (same as ingest).
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
 *   lat?: number,
 *   lng?: number,
 *   speed_kmh?: number,
 *   course_bearing?: number,
 *   track_id?: string,
 *   confidence?: number,
 *   resolve_status?: string,
 *   marker_id?: string,
 *   origin?: string,
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

  // Add server-side ID
  event._id = `feed_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;

  try {
    const redis = getRedis();
    const json = JSON.stringify(event);

    // LPUSH + LTRIM = circular buffer (newest first)
    const pipeline = redis.pipeline();
    pipeline.lpush(REDIS_FEED_KEY, json);
    pipeline.ltrim(REDIS_FEED_KEY, 0, MAX_FEED_ENTRIES - 1);
    pipeline.expire(REDIS_FEED_KEY, FEED_TTL_SECONDS);
    await pipeline.exec();

    // Broadcast to admin SSE listeners
    broadcastSSE({ type: 'admin_feed', data: event });
  } catch (err) {
    console.warn('[FEED] Redis write error:', err);
    return NextResponse.json({ error: 'Storage error' }, { status: 500 });
  }

  return NextResponse.json({ ok: true });
}
