import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

const DATA_DIR = process.env.DATA_DIR || '/data';
const MODERATORS_FILE = path.join(DATA_DIR, 'chat_moderators.json');
const MODERATOR_SECRET = process.env.AUTH_SECRET || '';

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
 * POST /api/chat/add-moderator
 * Add a device as chat moderator (requires secret).
 */
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { secret, deviceId } = body;

    if (!secret || !deviceId) {
      return NextResponse.json({ error: 'Відсутні обов\'язкові поля' }, { status: 400 });
    }

    if (secret !== MODERATOR_SECRET) {
      return NextResponse.json({ error: 'Невірний пароль' }, { status: 403 });
    }

    const mods = loadModerators();
    if (!mods.includes(deviceId)) {
      mods.push(deviceId);
      saveModerators(mods);
    }

    console.log(`[CHAT] Moderator added: ${deviceId}`);
    return NextResponse.json({ status: 'ok' });
  } catch (err) {
    console.error('[CHAT] Add-moderator error:', err);
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}
