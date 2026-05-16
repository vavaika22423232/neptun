import crypto from 'crypto';
import { getRedis } from '@/lib/redis';
import { normalizeMaritimeFeedEvent } from '@/lib/feed-maritime-normalize';

export const ADMIN_FEED_REDIS_KEY = 'admin:feed';
const ADMIN_FEED_MSG_META_PREFIX = 'admin:feed:msgmeta:';
const ADMIN_FEED_MAX = 500;
const ADMIN_FEED_TTL_SECONDS = 3 * 3600;
const ADMIN_FEED_DEDUP_WINDOW_SECONDS = 120;

export type AdminFeedEntry = Record<string, unknown> & {
  _id: string;
  ts: string;
  status: string;
  channel_name: string;
};

function cleanString(value: unknown, max: number): string {
  if (typeof value !== 'string') return '';
  return value.trim().slice(0, max);
}

function finiteNumber(value: unknown): number | undefined {
  if (typeof value !== 'number' || !Number.isFinite(value)) return undefined;
  return value;
}

function messageMetaKey(channelId: number, messageId: number): string {
  return `${ADMIN_FEED_MSG_META_PREFIX}${channelId}:${messageId}`;
}

export function normalizeAdminFeedEntry(input: Record<string, unknown>): AdminFeedEntry {
  const now = new Date().toISOString();
  const entry: Record<string, unknown> = { ...input };
  entry.ts = cleanString(entry.ts, 64) || now;
  entry.status = cleanString(entry.status, 64) || 'processed';
  entry.channel_name = cleanString(entry.channel_name, 128) || 'unknown';
  entry.msg_text = cleanString(entry.msg_text, 800);
  entry.reason = cleanString(entry.reason, 500);
  entry.channel_id = finiteNumber(entry.channel_id);
  entry.msg_id = finiteNumber(entry.msg_id);
  normalizeMaritimeFeedEvent(entry);

  const seed = [
    entry.ts,
    entry.channel_name,
    entry.msg_id,
    entry.status,
    entry.marker_id,
    entry.reason,
  ].join('|');
  return {
    ...entry,
    _id: crypto.createHash('sha1').update(seed).digest('hex').slice(0, 16),
    ts: String(entry.ts),
    status: String(entry.status),
    channel_name: String(entry.channel_name),
  };
}

export async function appendAdminFeedEntry(input: Record<string, unknown>): Promise<AdminFeedEntry> {
  const entry = normalizeAdminFeedEntry(input);
  const redis = getRedis();
  const serialized = JSON.stringify(entry);
  const channelId = finiteNumber(entry.channel_id) || 0;
  const messageId = finiteNumber(entry.msg_id) || 0;
  const nowSeconds = Date.now() / 1000;

  if (channelId && messageId) {
    const metaKey = messageMetaKey(channelId, messageId);
    const previousRaw = await redis.get(metaKey);
    if (previousRaw) {
      try {
        const previous = JSON.parse(previousRaw) as { t?: number; payload?: string };
        const previousTime = finiteNumber(previous.t) || 0;
        if (previous.payload && nowSeconds - previousTime < ADMIN_FEED_DEDUP_WINDOW_SECONDS) {
          await redis.lrem(ADMIN_FEED_REDIS_KEY, 1, previous.payload);
        }
      } catch {
        /* ignore bad dedup metadata */
      }
    }
    await redis.set(
      metaKey,
      JSON.stringify({ t: nowSeconds, payload: serialized }),
      'EX',
      ADMIN_FEED_TTL_SECONDS,
    );
  }

  const pipeline = redis.pipeline();
  pipeline.lpush(ADMIN_FEED_REDIS_KEY, serialized);
  pipeline.ltrim(ADMIN_FEED_REDIS_KEY, 0, ADMIN_FEED_MAX - 1);
  pipeline.expire(ADMIN_FEED_REDIS_KEY, ADMIN_FEED_TTL_SECONDS);
  await pipeline.exec();
  return entry;
}

export async function listAdminFeedEntries(
  limit: number,
  offset = 0,
): Promise<{ entries: AdminFeedEntry[]; total: number; limit: number; offset: number }> {
  const safeLimit = Math.max(1, Math.min(500, Math.floor(limit || 300)));
  const safeOffset = Math.max(0, Math.floor(offset || 0));
  const redis = getRedis();
  const [raw, total] = await Promise.all([
    redis.lrange(ADMIN_FEED_REDIS_KEY, safeOffset, safeOffset + safeLimit - 1),
    redis.llen(ADMIN_FEED_REDIS_KEY),
  ]);
  const entries: AdminFeedEntry[] = [];
  for (const item of raw) {
    try {
      const parsed = JSON.parse(item) as Record<string, unknown>;
      entries.push(normalizeAdminFeedEntry(parsed));
    } catch {
      /* skip malformed rows */
    }
  }
  return { entries, total, limit: safeLimit, offset: safeOffset };
}
