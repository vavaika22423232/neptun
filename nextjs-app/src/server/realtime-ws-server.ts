import Fastify from 'fastify';
import websocket from '@fastify/websocket';
import Redis from 'ioredis';
import type { RawData, WebSocket } from 'ws';

const REDIS_URL = process.env.REDIS_URL || 'redis://127.0.0.1:6379';
const SSE_CHANNEL = 'sse:broadcast';
const PORT = Number(process.env.THREAT_WS_PORT || 4001);

type ThreatEntity = {
  id: string;
  lat: number;
  lng: number;
  threat_type: string;
  bearing?: number | null;
  updated_at?: number;
};

type ThreatEntityUpdate =
  | { type: 'add'; entity: ThreatEntity }
  | { type: 'update'; entity: ThreatEntity }
  | { type: 'remove'; id: string };

type SocialCursorMessage = {
  type: 'cursor';
  id: string;
  lat: number;
  lng: number;
  nickname?: string;
  color?: string;
};

type ClientMessage = SocialCursorMessage | { type: 'ping' };

const fastify = Fastify({ logger: true });
const threatClients = new Set<WebSocket>();
const socialClients = new Set<WebSocket>();

function send(client: WebSocket, payload: unknown): void {
  if (client.readyState === client.OPEN) client.send(JSON.stringify(payload));
}

function broadcast(clients: Set<WebSocket>, payload: unknown, except?: WebSocket): void {
  const encoded = JSON.stringify(payload);
  for (const client of clients) {
    if (client !== except && client.readyState === client.OPEN) client.send(encoded);
  }
}

function numberFrom(value: unknown): number | null {
  const n = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

function markerToThreatEntity(raw: Record<string, unknown>): ThreatEntity | null {
  const lat = numberFrom(raw.lat);
  const lng = numberFrom(raw.lng);
  if (lat == null || lng == null) return null;
  const id = String(raw.track_id || raw.id || `${lat.toFixed(4)}_${lng.toFixed(4)}`);
  return {
    id,
    lat,
    lng,
    threat_type: String(raw.threat_type || raw.type || 'default'),
    bearing: numberFrom(raw.course_bearing ?? raw.ticker_bearing),
    updated_at: numberFrom(raw.last_update_epoch ?? raw.created_at_epoch) ?? Date.now(),
  };
}

function translateRedisEvent(raw: string): ThreatEntityUpdate | null {
  const event = JSON.parse(raw) as { type?: string; data?: Record<string, unknown> };
  if (event.type === 'marker_delete') {
    const id = String(event.data?.track_id || event.data?.id || '');
    return id ? { type: 'remove', id } : null;
  }
  if (event.type === 'marker_new' || event.type === 'marker_update') {
    const entity = markerToThreatEntity(event.data || {});
    return entity ? { type: 'add', entity } : null;
  }
  if (event.type === 'track_update') {
    const marker = event.data?.marker;
    const entity = marker && typeof marker === 'object' ? markerToThreatEntity(marker as Record<string, unknown>) : null;
    return entity ? { type: 'update', entity } : null;
  }
  return null;
}

function parseClientMessage(message: RawData): ClientMessage | null {
  const text = message.toString();
  if (text === 'ping') return { type: 'ping' };
  try {
    const parsed = JSON.parse(text) as Partial<SocialCursorMessage>;
    if (
      parsed.type === 'cursor' &&
      typeof parsed.id === 'string' &&
      typeof parsed.lat === 'number' &&
      typeof parsed.lng === 'number'
    ) {
      return {
        type: 'cursor',
        id: parsed.id.slice(0, 64),
        lat: parsed.lat,
        lng: parsed.lng,
        nickname: typeof parsed.nickname === 'string' ? parsed.nickname.slice(0, 32) : undefined,
        color: typeof parsed.color === 'string' ? parsed.color.slice(0, 24) : undefined,
      };
    }
  } catch {
    return null;
  }
  return null;
}

async function main() {
  await fastify.register(websocket, {
    options: {
      maxPayload: 1024 * 32,
      perMessageDeflate: false,
    },
  });

  fastify.get('/health', async () => ({
    ok: true,
    threatClients: threatClients.size,
    socialClients: socialClients.size,
  }));

  fastify.get('/ws/threats', { websocket: true }, (socket) => {
    threatClients.add(socket);
    send(socket, { type: 'hello', channel: 'threats' });
    socket.on('message', (message: RawData) => {
      if (message.toString() === 'ping') socket.send('pong');
    });
    socket.on('close', () => {
      threatClients.delete(socket);
    });
  });

  fastify.get('/ws/social', { websocket: true }, (socket) => {
    socialClients.add(socket);
    send(socket, { type: 'hello', channel: 'social' });
    socket.on('message', (message: RawData) => {
      const parsed = parseClientMessage(message);
      if (!parsed) return;
      if (parsed.type === 'ping') {
        socket.send('pong');
        return;
      }
      broadcast(socialClients, { ...parsed, ts: Date.now() }, socket);
    });
    socket.on('close', () => {
      socialClients.delete(socket);
    });
  });

  const redis = new Redis(REDIS_URL, { lazyConnect: true, maxRetriesPerRequest: null });
  await redis.connect();
  await redis.subscribe(SSE_CHANNEL);
  redis.on('message', (_channel, message) => {
    try {
      const translated = translateRedisEvent(message);
      if (translated) broadcast(threatClients, translated);
    } catch {
      // Drop malformed messages: realtime must remain non-blocking.
    }
  });

  await fastify.listen({ host: '0.0.0.0', port: PORT });
}

void main();
