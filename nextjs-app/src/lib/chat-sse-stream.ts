// SSE hub: client set, Redis pub/sub, debounced marker/online broadcasts.
// HTTP entry: `app/api/chat/stream/route.ts` exports GET only (Next.js route typing).

import { publishSSE, subscribeSSE, redisGetCount } from '@/lib/redis';
import { requireChatAuth } from '@/lib/chat-auth';

const MAX_SSE_CLIENTS = 10_000;
const MAX_SSE_PER_IP = 5;
const KEEPALIVE_INTERVAL = 55_000; // 55s — well within nginx 120s timeout
const MARKER_DEBOUNCE_MS = 2_000;  // Batch marker_new events within 2s window
const ONLINE_DEBOUNCE_MS = 5_000;  // Debounce online count broadcasts
const ONLINE_SYNC_INTERVAL = 90_000; // Sync Redis counter — rarer = less CPU across workers

const clients = new Set<ReadableStreamDefaultController>();
const ipCounts = new Map<string, number>();

const encoder = new TextEncoder();
const keepalivePayload = encoder.encode(': keepalive\n\n');

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

const SSE_WORKER_KEY = `sse:worker:${process.pid}`;
const SSE_WORKER_TTL = 60;

let _workerRegistered = false;

async function syncOnlineCounter() {
  try {
    const redis = (await import('@/lib/redis')).getRedis();
    await redis.set(SSE_WORKER_KEY, String(clients.size), 'EX', SSE_WORKER_TTL);
    if (!_workerRegistered) {
      _workerRegistered = true;
      await registerWorkerPid();
    }
  } catch { /* best-effort */ }
}

setInterval(() => {
  syncOnlineCounter();
}, ONLINE_SYNC_INTERVAL);

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

let _pendingMarker: Record<string, unknown> | null = null;
let _markerTimer: ReturnType<typeof setTimeout> | null = null;

let _onlineTimer: ReturnType<typeof setTimeout> | null = null;

function debouncedMarkerBroadcast(marker: Record<string, unknown>) {
  _pendingMarker = marker;
  if (_markerTimer) return;
  _markerTimer = setTimeout(() => {
    _markerTimer = null;
    if (_pendingMarker) {
      rawPublish({ type: 'marker_new', data: _pendingMarker });
      _pendingMarker = null;
    }
  }, MARKER_DEBOUNCE_MS);
}

const SSE_ONLINE_KEY = 'sse:online';

const WORKER_KEY_PREFIX = 'sse:worker:';
const WORKER_SET_KEY = 'sse:worker_pids';

async function registerWorkerPid(): Promise<void> {
  try {
    const redis = (await import('@/lib/redis')).getRedis();
    await redis.sadd(WORKER_SET_KEY, String(process.pid));
  } catch { /* best-effort */ }
}

async function getGlobalOnlineCount(): Promise<number> {
  try {
    const redis = (await import('@/lib/redis')).getRedis();
    const pids = await redis.smembers(WORKER_SET_KEY);
    if (pids.length === 0) return 0;
    const keys = pids.map((pid) => `${WORKER_KEY_PREFIX}${pid}`);
    const values = await redis.mget(...keys);
    let total = 0;
    const deadPids: string[] = [];
    for (let i = 0; i < values.length; i++) {
      const v = values[i];
      if (v) {
        total += parseInt(v, 10) || 0;
      } else {
        deadPids.push(pids[i]);
      }
    }
    if (deadPids.length > 0) {
      await redis.srem(WORKER_SET_KEY, ...deadPids);
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

function localBroadcast(event: { type: string; data: unknown }) {
  if (clients.size === 0) return;
  const encoded = encoder.encode(`data: ${JSON.stringify(event)}\n\n`);
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

let _subscribed = false;
function ensureSubscribed() {
  if (_subscribed) return;
  _subscribed = true;
  subscribeSSE((event) => {
    localBroadcast(event);
  });
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function rawPublish(event: { type: string; data: any }) {
  localBroadcast(event);
  publishSSE(event).catch(() => {
    // Redis failed; other workers won't get it, local clients already did
  });
}

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
  rawPublish(event);
}

export async function handleChatSSEGet(request: Request) {
  const authResult = requireChatAuth(request);
  if (authResult instanceof Response) return authResult;

  ensureSubscribed();

  const clientIP = request.headers.get('X-Real-IP')
    || request.headers.get('X-Forwarded-For')?.split(',')[0]?.trim()
    || 'unknown';

  if (clients.size >= MAX_SSE_CLIENTS) {
    return new Response(JSON.stringify({ error: 'Too many connections' }), {
      status: 503,
      headers: { 'Content-Type': 'application/json', 'Retry-After': '30' },
    });
  }

  const currentIPCount = ipCounts.get(clientIP) || 0;
  if (currentIPCount >= MAX_SSE_PER_IP) {
    return new Response(JSON.stringify({ error: 'Too many connections from this IP' }), {
      status: 429,
      headers: { 'Content-Type': 'application/json', 'Retry-After': '60' },
    });
  }

  ipCounts.set(clientIP, currentIPCount + 1);

  const stream = new ReadableStream({
    async start(controller) {
      clients.add(controller);
      (controller as unknown as { _clientIP: string })._clientIP = clientIP;

      await syncOnlineCounter();
      const count = await getGlobalOnlineCount();

      try {
        controller.enqueue(
          encoder.encode(
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
