import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import { containsForbiddenText } from '@/lib/chat-forbidden';

const DATA_DIR = process.env.DATA_DIR || '/data';
const NICKNAMES_FILE = path.join(DATA_DIR, 'chat_nicknames.json');

interface NicknameEntry {
  nickname: string;
  device_id: string;
  registered_at: string;
}

function loadNicknames(): NicknameEntry[] {
  try {
    if (fs.existsSync(NICKNAMES_FILE)) {
      return JSON.parse(fs.readFileSync(NICKNAMES_FILE, 'utf-8'));
    }
  } catch { /* empty */ }
  return [];
}

/**
 * POST /api/chat/check-nickname
 * Check if a nickname is available.
 */
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { nickname, deviceId } = body;

    if (!nickname || nickname.length < 2) {
      return NextResponse.json({ available: false, error: 'Нікнейм занадто короткий' });
    }

    if (nickname.length > 20) {
      return NextResponse.json({ available: false, error: 'Нікнейм занадто довгий' });
    }

    // Forbidden word check
    if (containsForbiddenText(nickname)) {
      return NextResponse.json({ available: false, error: 'Неприпустимий нікнейм' });
    }

    const nicknames = loadNicknames();
    const existing = nicknames.find((n) => n.nickname.toLowerCase() === nickname.toLowerCase());

    if (existing && existing.device_id !== deviceId) {
      return NextResponse.json({ available: false, error: 'Нікнейм зайнятий' });
    }

    return NextResponse.json({ available: true });
  } catch (err) {
    console.error('[CHAT] Check-nickname error:', err);
    return NextResponse.json({ available: false, error: 'Помилка перевірки' });
  }
}
