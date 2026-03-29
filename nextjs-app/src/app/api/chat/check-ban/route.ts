import { NextResponse } from 'next/server';
import { isBanned } from '@/lib/admin/data';

/**
 * POST /api/chat/check-ban
 * Check if a device/nickname is banned from chat.
 * Accepts { deviceId, nickname } — checks both.
 */
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { deviceId, nickname, hardwareId } = body;

    if (!deviceId && !nickname && !hardwareId) {
      return NextResponse.json({ banned: false });
    }

    const ban = isBanned(deviceId, nickname, hardwareId);

    return NextResponse.json({
      banned: !!ban,
      reason: ban?.reason || null,
    });
  } catch (err) {
    console.error('[CHAT] Check-ban error:', err);
    return NextResponse.json({ banned: false });
  }
}
