import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

const DATA_DIR = process.env.DATA_DIR || '/data';
const BANS_FILE = path.join(DATA_DIR, 'chat_bans.json');

interface BanEntry {
  device_id: string;
  nickname: string;
  reason: string;
  banned_at: string;
  banned_by?: string;
}

function loadBans(): BanEntry[] {
  try {
    if (fs.existsSync(BANS_FILE)) {
      return JSON.parse(fs.readFileSync(BANS_FILE, 'utf-8'));
    }
  } catch { /* empty */ }
  return [];
}

/**
 * POST /api/chat/check-ban
 * Check if a device is banned from chat.
 */
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { deviceId } = body;

    if (!deviceId) {
      return NextResponse.json({ banned: false });
    }

    const bans = loadBans();
    const ban = bans.find((b) => b.device_id === deviceId);

    return NextResponse.json({
      banned: !!ban,
      reason: ban?.reason || null,
    });
  } catch (err) {
    console.error('[CHAT] Check-ban error:', err);
    return NextResponse.json({ banned: false });
  }
}
