import { NextResponse } from 'next/server';
import { broadcastSSE } from '../stream/route';

// Track typing users with auto-expiry
const typingUsers = new Map<string, { nickname: string; expires: number }>();

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { deviceId, nickname, isTyping } = body;

    if (isTyping) {
      typingUsers.set(deviceId, { nickname, expires: Date.now() + 5000 });
    } else {
      typingUsers.delete(deviceId);
    }

    // Clean expired
    const now = Date.now();
    for (const [id, info] of typingUsers) {
      if (info.expires < now) typingUsers.delete(id);
    }

    // Broadcast current typing users
    const users = Array.from(typingUsers.values()).map((v) => v.nickname);
    broadcastSSE({ type: 'typing', data: { users } });

    return NextResponse.json({ status: 'ok' });
  } catch {
    return NextResponse.json({ status: 'ok' });
  }
}
