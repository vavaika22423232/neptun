import { NextResponse } from 'next/server';
import fs from 'fs';
import fsp from 'fs/promises';
import path from 'path';
import crypto from 'crypto';
import { broadcastSSE } from '@/lib/chat-sse-stream';
import { invalidateChatCache } from '../messages/route';
import { isBanned, isModeratorDevice } from '@/lib/admin/data';
import { containsForbiddenText } from '@/lib/chat-forbidden';
import { isNewUser } from '@/lib/chat-nicknames';
import { redisFixedWindowAllow } from '@/lib/redis-rate-limit';
import { ChatSendSchema } from '@/lib/api-schemas';

const DATA_DIR = process.env.DATA_DIR || '/data';
const CHAT_FILE = path.join(DATA_DIR, 'chat_messages.json');
const FALLBACK_CHAT_FILE = path.resolve(process.cwd(), '..', 'chat_messages.json');

const MAX_MESSAGE_LENGTH = 500;
const MAX_MESSAGES = 1000;

// ── Rate limiter with periodic cleanup ───────────────────────────────────
const rateLimiter = new Map<string, number>();
const RATE_LIMIT_MS = 3000;
const NEW_USER_RATE_LIMIT_MS = 60_000; // 1 msg/min for first 24h
const RATE_LIMIT_CLEANUP_INTERVAL = 120_000; // clean every 2min (fewer timer wakeups)

setInterval(() => {
  const cutoff = Date.now() - RATE_LIMIT_MS * 2;
  for (const [key, ts] of rateLimiter) {
    if (ts < cutoff) rateLimiter.delete(key);
  }
}, RATE_LIMIT_CLEANUP_INTERVAL);

// eslint-disable-next-line @typescript-eslint/no-explicit-any
async function loadMessages(filePath: string): Promise<any[]> {
  try {
    const raw = await fsp.readFile(filePath, 'utf-8');
    const data = JSON.parse(raw);
    return Array.isArray(data) ? data : data.messages || [];
  } catch { return []; }
}

function resolveChatFile(): string {
  return fs.existsSync(path.dirname(CHAT_FILE)) ? CHAT_FILE : FALLBACK_CHAT_FILE;
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

import { requireChatAuth } from '@/lib/chat-auth';

export async function POST(request: Request) {
  try {
    const authResult = requireChatAuth(request);
    if (authResult instanceof Response) return authResult;
    const identity = authResult;

    const rawBody = await request.json();
    const parsed = ChatSendSchema.safeParse(rawBody);
    if (!parsed.success) {
      return NextResponse.json({ error: parsed.error.issues[0]?.message || 'Invalid input' }, { status: 400 });
    }
    const body = parsed.data;

    const deviceId = identity.deviceId;
    const nickname = identity.nickname || 'Анонім';
    const userId = nickname;

    const hardwareId = body.hardwareId || body.hardware_id;
    const rawText = (body.message || body.text)!;
    const text = escapeHtml(rawText).trim(); // SANITIZATION
    
    if (!text) {
      return NextResponse.json({ error: 'Повідомлення порожнє після очищення' }, { status: 400 });
    }

    const replyToId = body.replyTo;
    const isPro = body.isPro === true;

    const clientIP = request.headers.get('X-Real-IP')
      || request.headers.get('X-Forwarded-For')?.split(',')[0]?.trim()
      || 'unknown';

    const ipOk = await redisFixedWindowAllow(`rl:chat:send:ip:${clientIP}`, 20, 60, false);
    if (!ipOk) {
      return NextResponse.json(
        { error: 'Забагато повідомлень з цієї IP. Зачекайте хвилину.' },
        { status: 429 },
      );
    }

    const rlId = crypto.createHash('sha256').update(String(deviceId)).digest('hex').slice(0, 40);
    const rlBucket = Math.floor(Date.now() / 60_000);
    const rlOk = await redisFixedWindowAllow(`rl:chat:send:${rlId}:${rlBucket}`, 30, 60);
    if (!rlOk) {
      return NextResponse.json(
        { error: 'Забагато повідомлень. Зачекайте хвилину.' },
        { status: 429 },
      );
    }

    // Rate limiting (stricter for new users: 1 msg/min in first 24h)
    const limitMs = isNewUser(deviceId) ? NEW_USER_RATE_LIMIT_MS : RATE_LIMIT_MS;
    const lastSent = rateLimiter.get(deviceId) || 0;
    if (Date.now() - lastSent < limitMs) {
      const retrySec = Math.ceil((limitMs - (Date.now() - lastSent)) / 1000);
      return NextResponse.json(
        {
          error:
            limitMs >= 60_000
              ? `Новий користувач: зачекайте ${retrySec} сек перед наступним повідомленням`
              : 'Занадто швидко, спробуйте ще раз',
        },
        { status: 429 }
      );
    }
    rateLimiter.set(deviceId, Date.now());

    // Check ban using cached data (30s TTL from admin/data.ts)
    if (isBanned(deviceId, userId, hardwareId)) {
      return NextResponse.json({ error: 'Ви заблоковані' }, { status: 403 });
    }

    // Content filter: forbid offensive language (moderators bypass)
    const isModerator = isModeratorDevice(deviceId);
    if (!isModerator && containsForbiddenText(text)) {
      return NextResponse.json(
        { error: 'Повідомлення містить неприйнятну лексику' },
        { status: 400 }
      );
    }

    const filePath = resolveChatFile();
    let messages = await loadMessages(filePath);

    // Build replyTo object if replying
    let replyTo: any = null;
    if (replyToId) {
      const original = messages.find((m) => m.id === replyToId);
      if (original) {
        const author = original.userId || original.nickname || 'Анонім';
        replyTo = {
          id: original.id,
          userId: author,
          nickname: author, 
          message: escapeHtml(original.message || original.text || '').slice(0, 100),
        };
      }
    }

    const now = Date.now() / 1000;
    const nowDate = new Date();

    const message = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      userId,
      deviceId,
      message: text,
      timestamp: now,
      time: `${nowDate.getHours().toString().padStart(2, '0')}:${nowDate.getMinutes().toString().padStart(2, '0')}`,
      date: `${nowDate.getDate().toString().padStart(2, '0')}.${(nowDate.getMonth() + 1).toString().padStart(2, '0')}.${nowDate.getFullYear()}`,
      isModerator,
      isPro,
      replyTo,
      reactions: {},
    };

    messages.push(message);
    if (messages.length > MAX_MESSAGES) {
      messages = messages.slice(-MAX_MESSAGES);
    }

    // Atomic write (tmp + rename)
    const tmp = filePath + '.tmp.' + crypto.randomBytes(4).toString('hex');
    await fsp.writeFile(tmp, JSON.stringify(messages), 'utf-8');
    await fsp.rename(tmp, filePath);

    // Invalidate chat messages cache so next GET sees the new message
    invalidateChatCache();

    // Include deviceId so clients align outgoing bubbles with the sender (see messages GET).
    broadcastSSE({ type: 'new_message', data: message });

    return NextResponse.json({ status: 'ok', message });
  } catch (err) {
    console.error('[CHAT] Send error:', err);
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}
