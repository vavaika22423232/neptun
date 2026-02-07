import { NextResponse } from 'next/server';

/**
 * POST /api/chat/typing
 * Notify that a user is typing. Fire-and-forget.
 * In a real-time system this would broadcast via SSE/WebSocket.
 */
export async function POST(request: Request) {
  try {
    const body = await request.json();
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { deviceId, nickname, isTyping } = body;
    // Typing indicators are ephemeral — no persistence needed.
    // When SSE is implemented, broadcast here.
    return NextResponse.json({ status: 'ok' });
  } catch {
    return NextResponse.json({ status: 'ok' });
  }
}
