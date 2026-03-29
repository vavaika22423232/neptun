// SSE stream for real-time chat events
// Flutter connects here for new_message, delete_message, typing, reaction events
//
// Architecture (PM2 cluster-safe):
// - broadcastSSE() publishes to Redis Pub/Sub channel
// - Each worker subscribes and pushes to its LOCAL clients only
// - This means a marker ingested on worker #1 reaches SSE clients on worker #3
//
// Performance optimizations:
// - Keepalive interval: 55s (nginx proxy_read_timeout is 120s)
// - Debounced broadcasts: marker_new, online batched with 2s window
// - Online count: debounced 5s (many connect/disconnect per second)

import { publishSSE, subscribeSSE, redisGetCount } from '@/lib/redis';

const MAX_SSE_CLIENTS = 10_000;
const MAX_SSE_PER_IP = 5;
const KEEPALIVE_INTERVAL = 55_000; // 55s — well within nginx 120s timeout
const MARKER_DEBOUNCE_MS = 2_000;  // Batch marker_new events within 2s window
const ONLINE_DEBOUNCE_MS = 5_000;  // Debounce online count broadcasts
const ONLINE_SYNC_INTERVAL = 30_000; // Sync Redis counter with real client count every 30s

const clients = new Set<ReadableStreamDefaultController>();
const ipCounts = new Map<string, number>();

const keepalivePayload = new TextEncoder().encode(': keepalive\n\n');

setInterval(() => {
  if (clients.size === 0) return;
  const deadClients: ReadableStreamDefaultController[] = [];
  clients.forEach((controller) => {
    try {
      controller.enqueue(keepalivePayload);
    } catch {
      deadClients.push(controller);
    }
  });
  cleanupDead(deadClients);
}, KEEPALIVE_INTERVAL);

export function getSSEClientCount(): number {
  return clients.size;
}

// Each PM2 worker stores its own client count in a per-pid Redis key.
// The global online count is the sum of all workers' keys.
// This prevents drift from missed DECR calls during crashes / 502s.
const SSE_WORKER_KEY = `sse:worker:${process.pid}`;
const SSE_WORKER_TTL = 60; // auto-expire if worker dies without cleanup

async function syncOnlineCounter() {
  try {
    const redis = (await import('@/lib/redis')).getRedis();
    await redis.set(SSE_WORKER_KEY, String(clients.size), 'EX', SSE_WORKER_TTL);
  } catch { /* best-effort */ }
}

setInterval(() => {
  syncOnlineCounter();
}, ONLINE_SYNC_INTERVAL);

setInterval(() => {
  if (clients.size > 0) {
    console.log(`[SSE] ${clients.size} active connections (pid=${process.pid})`);
  }
  syncOnlineCounter();
}, 60_000);

// ── Cleanup helper ───────────────────────────────────────────────────────────

function cleanupDead(deadClients: ReadableStreamDefaultController[]) {
  for (const c of deadClients) {
    clients.delete(c);
    const ip = (c as unknown as { _clientIP?: string })._clientIP;
    if (ip) {
      const count = (ipCounts.get(ip) || 1) - 1;
      if (count <= 0) ipCounts.delete(ip);
      else ipCounts.set(ip, count);
    }
  }
}

// ── Debounced broadcast logic ────────────────────────────────────────────────

let _pendingMarker: Record<string, unknown> | null = null;
let _markerTimer: ReturnType<typeof setTimeout> | null = null;

let _onlineTimer: ReturnType<typeof setTimeout> | null = null;

function debouncedMarkerBroadcast(marker: Record<string, unknown>) {
  // Keep only the latest marker — clients will fetch full list anyway
  _pendingMarker = marker;
  if (_markerTimer) return; // already scheduled
  _markerTimer = setTimeout(() => {
    _markerTimer = null;
    if (_pendingMarker) {
      rawPublish({ type: 'marker_new', data: _pendingMarker });
      _pendingMarker = null;
    }
  }, MARKER_DEBOUNCE_MS);
}

const SSE_ONLINE_KEY = 'sse:online';

async function getGlobalOnlineCount(): Promise<number> {
  try {
    const redis = (await import('@/lib/redis')).getRedis();
    const keys = await redis.keys('sse:worker:*');
    if (keys.length === 0) return 0;
    const values = await redis.mget(...keys);
    let total = 0;
    for (const v of values) {
      if (v) total += parseInt(v, 10) || 0;
    }
    await redis.set(SSE_ONLINE_KEY, String(total));
    return total;
  } catch {
    return await redisGetCount(SSE_ONLINE_KEY);
  }
}

function debouncedOnlineBroadcast() {
  if (_onlineTimer) return;
  _onlineTimer = setTimeout(async () => {
    _onlineTimer = null;
    const count = await getGlobalOnlineCount();
    rawPublish({ type: 'online', data: { online: count } });
  }, ONLINE_DEBOUNCE_MS);
}

// ── Local broadcast (only to clients on THIS worker) ─────────────────────────

function localBroadcast(event: { type: string; data: unknown }) {
  if (clients.size === 0) return;
  const payload = `data: ${JSON.stringify(event)}\n\n`;
  const encoded = new TextEncoder().encode(payload);
  const deadClients: ReadableStreamDefaultController[] = [];

  clients.forEach((controller) => {
    try {
      controller.enqueue(encoded);
    } catch {
      deadClients.push(controller);
    }
  });

  cleanupDead(deadClients);
}

// ── Subscribe to Redis Pub/Sub — receives events from ALL workers ────────────
let _subscribed = false;
function ensureSubscribed() {
  if (_subscribed) return;
  _subscribed = true;
  subscribeSSE((event) => {
    localBroadcast(event);
  });
}

// ── Raw publish (bypasses debounce) ──────────────────────────────────────────
// Redis Pub/Sub does NOT deliver to the publisher, so we must localBroadcast
// so clients on this worker also receive immediate events (new_message, etc.)

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function rawPublish(event: { type: string; data: any }) {
  localBroadcast(event);
  publishSSE(event).catch(() => {
    // Redis failed; other workers won't get it, local clients already did
  });
}

// ── Public API: publish to Redis → all workers broadcast locally ─────────────
// Marker and online events are debounced; everything else is immediate.

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function broadcastSSE(event: { type: string; data: any }) {
  if (event.type === 'marker_new') {
    debouncedMarkerBroadcast(event.data);
    return;
  }
  if (event.type === 'online') {
    debouncedOnlineBroadcast();
    return;
  }
  // All other events (alarm_update, new_message, etc.) — immediate
  rawPublish(event);
}

export async function GET(request: Request) {
  // Ensure this worker is subscribed to Redis Pub/Sub
  ensureSubscribed();

  // Get client IP from nginx X-Real-IP header
  const clientIP = request.headers.get('X-Real-IP')
    || request.headers.get('X-Forwarded-For')?.split(',')[0]?.trim()
    || 'unknown';

  // Reject if at global capacity
  if (clients.size >= MAX_SSE_CLIENTS) {
    return new Response(JSON.stringify({ error: 'Too many connections' }), {
      status: 503,
      headers: { 'Content-Type': 'application/json', 'Retry-After': '30' },
    });
  }

  // Reject if this IP has too many connections
  const currentIPCount = ipCounts.get(clientIP) || 0;
  if (currentIPCount >= MAX_SSE_PER_IP) {
    return new Response(JSON.stringify({ error: 'Too many connections from this IP' }), {
      status: 429,
      headers: { 'Content-Type': 'application/json', 'Retry-After': '60' },
    });
  }

  // Track IP
  ipCounts.set(clientIP, currentIPCount + 1);

  const stream = new ReadableStream({
    async start(controller) {
      clients.add(controller);
      (controller as unknown as { _clientIP: string })._clientIP = clientIP;

      await syncOnlineCounter();
      const count = await getGlobalOnlineCount();

      try {
        controller.enqueue(
          new TextEncoder().encode(
            `data: ${JSON.stringify({ type: 'connected', data: { online: count, pid: process.pid } })}\n\n`
          )
        );
      } catch { /* ignore */ }
    },
    async cancel(controller) {
      clients.delete(controller);
      const ip = (controller as unknown as { _clientIP?: string })._clientIP;
      if (ip) {
        const count = (ipCounts.get(ip) || 1) - 1;
        if (count <= 0) ipCounts.delete(ip);
        else ipCounts.set(ip, count);
      }
      await syncOnlineCounter();
      debouncedOnlineBroadcast();
    },
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      Connection: 'keep-alive',
      'X-Accel-Buffering': 'no',
    },
  });
}
