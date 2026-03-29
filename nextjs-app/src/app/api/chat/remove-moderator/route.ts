import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import { getAdminHeaderSecret, safeCompare } from '@/lib/server-secrets';

const DATA_DIR = process.env.DATA_DIR || '/data';
const MODERATORS_FILE = path.join(DATA_DIR, 'chat_moderators.json');

function loadModerators(): string[] {
  try {
    if (fs.existsSync(MODERATORS_FILE)) {
      return JSON.parse(fs.readFileSync(MODERATORS_FILE, 'utf-8'));
    }
  } catch { /* empty */ }
  return [];
}

function saveModerators(mods: string[]) {
  const dir = path.dirname(MODERATORS_FILE);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(MODERATORS_FILE, JSON.stringify(mods, null, 2), 'utf-8');
}

/**
 * POST /api/chat/remove-moderator
 * Remove a device from chat moderators (requires secret).
 */
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { secret, deviceId } = body;

    if (!secret || !deviceId) {
      return NextResponse.json({ error: 'Missing fields' }, { status: 400 });
    }

    const modSecret = getAdminHeaderSecret();
    if (!modSecret || !safeCompare(secret, modSecret)) {
      return NextResponse.json({ error: 'Невірний пароль' }, { status: 403 });
    }

    const mods = loadModerators();
    const filtered = mods.filter((m) => m !== deviceId);
    saveModerators(filtered);

    console.log(`[CHAT] Moderator removed: ${deviceId}`);
    return NextResponse.json({ status: 'ok' });
  } catch (err) {
    console.error('[CHAT] Remove-moderator error:', err);
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}
