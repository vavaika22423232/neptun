import { NextResponse } from 'next/server';
import crypto from 'crypto';
import { getJwtSecret } from '@/lib/server-secrets';
import { redisFixedWindowAllow } from '@/lib/redis-rate-limit';
import { getClientIp, ipRedisTag } from '@/lib/client-ip';
import { AuthTokenSchema } from '@/lib/api-schemas';
import { getNicknameForDevice } from '@/lib/chat-nicknames';

const ACCESS_TTL = 3600;  // 1 hour
const REFRESH_TTL = 86400 * 30; // 30 days
const TOKEN_RATE_LIMIT = 10; // max requests per window
const TOKEN_RATE_WINDOW = 60; // 60 second window

function createToken(secret: string, payload: Record<string, unknown>, expiresIn: number): string {
  const header = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).toString('base64url');
  const now = Math.floor(Date.now() / 1000);
  const body = Buffer.from(JSON.stringify({ ...payload, iat: now, exp: now + expiresIn })).toString('base64url');
  const signature = crypto.createHmac('sha256', secret).update(`${header}.${body}`).digest('base64url');
  return `${header}.${body}.${signature}`;
}

export async function POST(request: Request) {
  try {
    const ip = getClientIp(request);
    const rateLimitKey = `rl:auth:token:${ipRedisTag(ip)}`;
    const allowed = await redisFixedWindowAllow(rateLimitKey, TOKEN_RATE_LIMIT, TOKEN_RATE_WINDOW, false);
    if (!allowed) {
      return NextResponse.json({ error: 'Too many requests' }, { status: 429 });
    }

    const secret = getJwtSecret();
    if (!secret) {
      console.error('[AUTH] JWT_SECRET / AUTH_SECRET not configured');
      return NextResponse.json({ error: 'Server misconfigured' }, { status: 500 });
    }

    const body = await request.json();
    const parsed = AuthTokenSchema.safeParse(body);
    if (!parsed.success) {
      return NextResponse.json({ error: parsed.error.issues[0]?.message || 'Invalid input' }, { status: 400 });
    }
    const { deviceId } = parsed.data;
    
    // STRICT DEVICE ID VALIDATION
    if (!deviceId || deviceId === 'null' || deviceId === 'undefined' || deviceId.length < 8) {
      return NextResponse.json({ error: 'Invalid Device ID' }, { status: 400 });
    }

    // Prefer server registry: client may omit nick or still send "Анонім" while user is registered.
    let nickname = (parsed.data.nickname || '').trim();
    if (!nickname || nickname === 'null' || nickname === 'undefined') {
      nickname = '';
    }
    const registered = getNicknameForDevice(deviceId);
    if (registered && registered.length > 0) {
      nickname = registered;
    } else if (!nickname) {
      nickname = 'Анонім';
    }

    // SENSITIVE NICKNAME PROTECTION
    const sensitive = ['admin', 'moderator', 'system', 'neptun', 'модератор', 'адмін'];
    const isSensitive = sensitive.some(s => nickname.toLowerCase().includes(s));
    
    if (isSensitive) {
      const adminSecret = process.env.ADMIN_SECRET || process.env.AUTH_SECRET;
      const providedSecret = request.headers.get('X-Admin-Secret') || '';
      if (!adminSecret || providedSecret !== adminSecret) {
        // Force generic name if attempt to spoof admin/mod
        nickname = 'Анонім';
      }
    }

    const accessToken = createToken(secret, { deviceId, nickname, type: 'access' }, ACCESS_TTL);
    // Refresh token must carry nickname too; otherwise /api/auth/refresh issues access JWT without nick
    // and every chat send becomes "Анонім" after the first hour.
    const refreshToken = createToken(secret, { deviceId, nickname, type: 'refresh' }, REFRESH_TTL);

    return NextResponse.json({
      access_token: accessToken,
      refresh_token: refreshToken,
      expires_in: ACCESS_TTL,
    });
  } catch (err) {
    console.error('[AUTH] Token error:', err);
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}
