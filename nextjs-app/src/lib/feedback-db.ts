/**
 * Feedback storage backed by Redis.
 *
 * Replaces better-sqlite3 which required native binaries compiled
 * per-platform (macOS build won't work on Linux server).
 *
 * Redis keys:
 * - feedback:{id}         — Hash with all ticket fields
 * - feedback:ids          — Sorted set (score = timestamp ms) for ordering
 * - feedback:responses:{id} — List of JSON-encoded response objects
 */

import { getRedis } from '@/lib/redis';

// ── Types ────────────────────────────────────────────────────────────────────

export interface FeedbackTicket {
  id: string;
  message: string;
  type: string;
  device_id: string;
  device: string;
  app_version: string;
  regions: string; // JSON array
  status: string;
  created_at: string;
  updated_at: string;
  last_read_at: string;
}

export interface FeedbackResponse {
  id: string;
  feedback_id: string;
  message: string;
  author: string;
  created_at: string;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function ticketKey(id: string) { return `feedback:${id}`; }
function responsesKey(id: string) { return `feedback:responses:${id}`; }
const INDEX_KEY = 'feedback:ids';

// ── Public API ───────────────────────────────────────────────────────────────

/** Insert a new feedback ticket */
export async function insertFeedback(ticket: FeedbackTicket): Promise<void> {
  const redis = getRedis();
  const key = ticketKey(ticket.id);
  const score = new Date(ticket.created_at).getTime();

  const pipeline = redis.pipeline();
  pipeline.hset(key, ticket as unknown as Record<string, string>);
  pipeline.zadd(INDEX_KEY, score.toString(), ticket.id);
  await pipeline.exec();
}

/** Get a single feedback ticket by ID */
export async function getFeedback(id: string): Promise<FeedbackTicket | null> {
  const raw = await getRedis().hgetall(ticketKey(id));
  if (!raw || !raw.id) return null;
  return raw as unknown as FeedbackTicket;
}

/** Update specific fields of a feedback ticket */
export async function updateFeedback(id: string, fields: Partial<FeedbackTicket>): Promise<void> {
  const redis = getRedis();
  const exists = await redis.exists(ticketKey(id));
  if (!exists) return;
  await redis.hset(ticketKey(id), fields as unknown as Record<string, string>);
}

/** Get responses for a ticket */
export async function getResponses(feedbackId: string): Promise<FeedbackResponse[]> {
  const raw = await getRedis().lrange(responsesKey(feedbackId), 0, -1);
  return raw.map(r => JSON.parse(r) as FeedbackResponse);
}

/** Add a response to a ticket */
export async function addResponse(resp: FeedbackResponse): Promise<void> {
  await getRedis().rpush(responsesKey(resp.feedback_id), JSON.stringify(resp));
}

/** List feedback tickets with optional filters */
export async function listFeedback(opts: {
  device_id?: string;
  status?: string;
  limit?: number;
}): Promise<{ tickets: FeedbackTicket[]; total: number }> {
  const redis = getRedis();
  const limit = opts.limit || 50;

  // Get all IDs sorted by created_at descending
  const allIds = await redis.zrevrange(INDEX_KEY, 0, -1);
  if (allIds.length === 0) return { tickets: [], total: 0 };

  // Fetch all tickets in bulk via pipeline
  const pipeline = redis.pipeline();
  for (const id of allIds) {
    pipeline.hgetall(ticketKey(id));
  }
  const results = await pipeline.exec();
  if (!results) return { tickets: [], total: 0 };

  let tickets: FeedbackTicket[] = [];
  for (const [err, raw] of results) {
    if (err || !raw || typeof raw !== 'object') continue;
    const t = raw as unknown as FeedbackTicket;
    if (!t.id) continue;
    // Apply filters
    if (opts.device_id && t.device_id !== opts.device_id) continue;
    if (opts.status && t.status !== opts.status) continue;
    tickets.push(t);
  }

  const total = tickets.length;
  tickets = tickets.slice(0, limit);
  return { tickets, total };
}

/** Delete a feedback ticket and its responses */
export async function deleteFeedback(id: string): Promise<void> {
  const redis = getRedis();
  const pipeline = redis.pipeline();
  pipeline.del(ticketKey(id));
  pipeline.del(responsesKey(id));
  pipeline.zrem(INDEX_KEY, id);
  await pipeline.exec();
}
