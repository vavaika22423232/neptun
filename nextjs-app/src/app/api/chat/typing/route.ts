import { NextResponse } from 'next/server';
import { broadcastSSE } from '../stream/route';
import { isBanned } from '@/lib/admin/data';

// Track typing users with auto-expiry
const typingUsers = new Map<string, { nickname: string; expires: number }>();

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { deviceId, nickname, hardwareId, isTyping } = body;

    // Silently ignore banned users
    if (isBanned(deviceId, nickname, hardwareId)) {
      return NextResponse.json({ status: 'ok' });
    }

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
