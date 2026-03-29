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
  hardware_id?: string;
}

function loadNicknames(): NicknameEntry[] {
  try {
    if (fs.existsSync(NICKNAMES_FILE)) {
      return JSON.parse(fs.readFileSync(NICKNAMES_FILE, 'utf-8'));
    }
  } catch { /* empty */ }
  return [];
}

function saveNicknames(entries: NicknameEntry[]) {
  const dir = path.dirname(NICKNAMES_FILE);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(NICKNAMES_FILE, JSON.stringify(entries, null, 2), 'utf-8');
}

/**
 * POST /api/chat/register-nickname
 * Register a nickname for a device.
 */
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { nickname, deviceId, hardwareId } = body;

    if (!nickname || !deviceId) {
      return NextResponse.json({ success: false, error: 'Відсутні обов\'язкові поля' });
    }

    if (nickname.length < 2 || nickname.length > 20) {
      return NextResponse.json({ success: false, error: 'Нікнейм має бути від 2 до 20 символів' });
    }

    // Sensitive nickname protection
    const sensitive = ['admin', 'moderator', 'system', 'neptun', 'модератор', 'адмін'];
    if (sensitive.some(s => nickname.toLowerCase().includes(s))) {
      return NextResponse.json({ success: false, error: 'Нікнейм містить службове слово' });
    }

    // Forbidden word check
    if (containsForbiddenText(nickname)) {
      return NextResponse.json({ success: false, error: 'Неприпустимий нікнейм' });
    }

    const nicknames = loadNicknames();
    const existing = nicknames.find((n) => n.nickname.toLowerCase() === nickname.toLowerCase());

    if (existing && existing.device_id !== deviceId) {
      return NextResponse.json({ success: false, error: 'Нікнейм зайнятий' });
    }

    // Remove old nickname for this device
    const filtered = nicknames.filter((n) => n.device_id !== deviceId);
    const entry: NicknameEntry = {
      nickname,
      device_id: deviceId,
      registered_at: new Date().toISOString(),
    };
    if (hardwareId && typeof hardwareId === 'string') entry.hardware_id = hardwareId;
    filtered.push(entry);

    saveNicknames(filtered);
    return NextResponse.json({ success: true });
  } catch (err) {
    console.error('[CHAT] Register-nickname error:', err);
    return NextResponse.json({ success: false, error: 'Помилка реєстрації' });
  }
}
