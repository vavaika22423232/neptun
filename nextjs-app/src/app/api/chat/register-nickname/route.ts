import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import { ChatRegisterNicknameSchema } from '@/lib/api-schemas';
import { containsForbiddenText } from '@/lib/chat-forbidden';
import { requireDeviceAuthFromJson } from '@/lib/device-auth';
import { getClientIp, ipRedisTag } from '@/lib/client-ip';
import { redisFixedWindowAllow } from '@/lib/redis-rate-limit';
import { logSecurityEvent } from '@/lib/security-log';

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

function isReservedDisplayNickname(nickname: string): boolean {
  return ['анонім', 'anonymous', 'anon'].includes(nickname.trim().toLowerCase());
}

/**
 * POST /api/chat/register-nickname
 * Register a nickname for the authenticated device.
 */
export async function POST(request: Request) {
  try {
    const ip = getClientIp(request);
    const allowed = await redisFixedWindowAllow(
      `rl:chat:register_nick:${ipRedisTag(ip)}`,
      10,
      3600,
      false,
    );
    if (!allowed) {
      logSecurityEvent('rate_limit_hit', { route: 'chat_register_nickname' });
      return NextResponse.json({ success: false, error: 'Забагато спроб' }, { status: 429 });
    }

    const body = await request.json();
    const auth = await requireDeviceAuthFromJson(request, body);
    if (!auth.ok) {
      return NextResponse.json({ success: false, error: 'Потрібна авторизація' }, { status: auth.response.status });
    }

    const parsed = ChatRegisterNicknameSchema.safeParse(body);
    if (!parsed.success) {
      return NextResponse.json({ success: false, error: 'Невірний нікнейм' }, { status: 400 });
    }

    const { nickname, hardwareId } = parsed.data;
    const deviceId = auth.deviceId;

    if (isReservedDisplayNickname(nickname)) {
      return NextResponse.json({ success: false, error: 'Цей нікнейм зарезервований системою' });
    }

    const sensitive = ['admin', 'moderator', 'system', 'neptun', 'модератор', 'адмін'];
    if (sensitive.some((s) => nickname.toLowerCase().includes(s))) {
      return NextResponse.json({ success: false, error: 'Нікнейм містить службове слово' });
    }

    if (containsForbiddenText(nickname)) {
      return NextResponse.json({ success: false, error: 'Неприпустимий нікнейм' });
    }

    const nicknames = loadNicknames();
    const existing = nicknames.find((n) => n.nickname.toLowerCase() === nickname.toLowerCase());

    if (existing && existing.device_id !== deviceId) {
      return NextResponse.json({ success: false, error: 'Нікнейм зайнятий' });
    }

    const filtered = nicknames.filter((n) => n.device_id !== deviceId);
    const entry: NicknameEntry = {
      nickname,
      device_id: deviceId,
      registered_at: new Date().toISOString(),
    };
    if (hardwareId) entry.hardware_id = hardwareId;
    filtered.push(entry);

    saveNicknames(filtered);
    return NextResponse.json({ success: true });
  } catch (err) {
    console.error('[CHAT] Register-nickname error:', err);
    return NextResponse.json({ success: false, error: 'Помилка реєстрації' });
  }
}
