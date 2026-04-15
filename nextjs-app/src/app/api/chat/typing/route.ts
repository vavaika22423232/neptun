import { NextResponse } from 'next/server';
import { broadcastSSE } from '@/lib/chat-sse-stream';
import { isBanned } from '@/lib/admin/data';
import { requireChatAuth } from '@/lib/chat-auth';

const typingUsers = new Map<string, { nickname: string; expires: number }>();
const typingRateLimit = new Map<string, number>();
const TYPING_COOLDOWN_MS = 2000;

setInterval(() => {
  const cutoff = Date.now() - TYPING_COOLDOWN_MS * 3;
  for (const [k, ts] of typingRateLimit) {
    if (ts < cutoff) typingRateLimit.delete(k);
  }
}, 60_000);

export async function POST(request: Request) {
  try {
    const authResult = requireChatAuth(request);
    if (authResult instanceof Response) return authResult;
    const identity = authResult;

    const body = await request.json();
    const { hardwareId, isTyping } = body;

    const deviceId = identity.deviceId;

    if (isBanned(deviceId, identity.nickname, hardwareId)) {
      return NextResponse.json({ status: 'ok' });
    }

    const lastTyping = typingRateLimit.get(deviceId) || 0;
    if (Date.now() - lastTyping < TYPING_COOLDOWN_MS) {
      return NextResponse.json({ status: 'ok' });
    }
    typingRateLimit.set(deviceId, Date.now());

    const safeName = (identity.nickname || 'Анонім').slice(0, 30);

    if (isTyping) {
      typingUsers.set(deviceId, { nickname: safeName, expires: Date.now() + 5000 });
    } else {
      typingUsers.delete(deviceId);
    }

    const now = Date.now();
    for (const [id, info] of typingUsers) {
      if (info.expires < now) typingUsers.delete(id);
    }

    const users = Array.from(typingUsers.values()).map((v) => v.nickname);
    broadcastSSE({ type: 'typing', data: { users } });

    return NextResponse.json({ status: 'ok' });
  } catch {
    return NextResponse.json({ status: 'ok' });
  }
}
