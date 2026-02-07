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
 * GET /api/chat/ban-list
 * Get list of banned nicknames (moderator action).
 */
export async function GET() {
  const bans = loadBans();
  return NextResponse.json({
    banned: bans.map((b) => b.nickname),
  });
}
