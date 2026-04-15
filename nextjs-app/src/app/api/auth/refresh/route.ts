import { NextResponse } from 'next/server';
import crypto from 'crypto';
import { getJwtSecret } from '@/lib/server-secrets';
import { resolveChatDisplayNickname } from '@/lib/chat-nicknames';

const ACCESS_TTL = 3600;

function verifyToken(secret: string, token: string): Record<string, unknown> | null {
  try {
    const [header, body, signature] = token.split('.');
    const expected = crypto.createHmac('sha256', secret).update(`${header}.${body}`).digest('base64url');
    if (signature !== expected) return null;
    const payload = JSON.parse(Buffer.from(body, 'base64url').toString('utf-8'));
    if (payload.exp && payload.exp < Math.floor(Date.now() / 1000)) return null;
    return payload;
  } catch {
    return null;
  }
}

function createToken(secret: string, payload: Record<string, unknown>, expiresIn: number): string {
  const header = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).toString('base64url');
  const now = Math.floor(Date.now() / 1000);
  const body = Buffer.from(JSON.stringify({ ...payload, iat: now, exp: now + expiresIn })).toString('base64url');
  const signature = crypto.createHmac('sha256', secret).update(`${header}.${body}`).digest('base64url');
  return `${header}.${body}.${signature}`;
}

/**
 * POST /api/auth/refresh
 * Refresh an access token using a valid refresh token.
 */
export async function POST(request: Request) {
  try {
    const secret = getJwtSecret();
    if (!secret) {
      console.error('[AUTH] JWT_SECRET / AUTH_SECRET not configured');
      return NextResponse.json({ error: 'Server misconfigured' }, { status: 500 });
    }

    const body = await request.json();
    const { refresh_token } = body;

    if (!refresh_token) {
      return NextResponse.json({ error: 'Missing refresh_token' }, { status: 400 });
    }

    const payload = verifyToken(secret, refresh_token);
    if (!payload || payload.type !== 'refresh') {
      return NextResponse.json({ error: 'Invalid refresh token' }, { status: 401 });
    }

    const deviceId = String(payload.deviceId);
    const fromJwt =
      typeof payload.nickname === 'string' ? payload.nickname.trim() : '';
    const nickname = resolveChatDisplayNickname(deviceId, fromJwt);

    const accessToken = createToken(
      secret,
      { deviceId, nickname, type: 'access' },
      ACCESS_TTL
    );

    return NextResponse.json({
      access_token: accessToken,
      expires_in: ACCESS_TTL,
    });
  } catch (err) {
    console.error('[AUTH] Refresh error:', err);
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}
