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

function saveBans(bans: BanEntry[]) {
  const dir = path.dirname(BANS_FILE);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(BANS_FILE, JSON.stringify(bans, null, 2), 'utf-8');
}

/**
 * POST /api/chat/unban
 * Unban a user from chat (moderator action).
 */
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { nickname } = body;

    if (!nickname) {
      return NextResponse.json({ error: 'Missing nickname' }, { status: 400 });
    }

    const bans = loadBans();
    const filtered = bans.filter((b) => b.nickname.toLowerCase() !== nickname.toLowerCase());
    saveBans(filtered);

    console.log(`[CHAT] Unbanned: ${nickname}`);
    return NextResponse.json({ status: 'ok' });
  } catch (err) {
    console.error('[CHAT] Unban error:', err);
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}
