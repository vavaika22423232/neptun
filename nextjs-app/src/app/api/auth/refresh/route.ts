import { NextResponse } from 'next/server';
import crypto from 'crypto';

const JWT_SECRET = process.env.AUTH_SECRET || 'default-secret';
const ACCESS_TTL = 3600;

function verifyToken(token: string): Record<string, unknown> | null {
  try {
    const [header, body, signature] = token.split('.');
    const expected = crypto.createHmac('sha256', JWT_SECRET).update(`${header}.${body}`).digest('base64url');
    if (signature !== expected) return null;
    const payload = JSON.parse(Buffer.from(body, 'base64url').toString('utf-8'));
    if (payload.exp && payload.exp < Math.floor(Date.now() / 1000)) return null;
    return payload;
  } catch {
    return null;
  }
}

function createToken(payload: Record<string, unknown>, expiresIn: number): string {
  const header = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).toString('base64url');
  const now = Math.floor(Date.now() / 1000);
  const body = Buffer.from(JSON.stringify({ ...payload, iat: now, exp: now + expiresIn })).toString('base64url');
  const signature = crypto.createHmac('sha256', JWT_SECRET).update(`${header}.${body}`).digest('base64url');
  return `${header}.${body}.${signature}`;
}

/**
 * POST /api/auth/refresh
 * Refresh an access token using a valid refresh token.
 */
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { refresh_token } = body;

    if (!refresh_token) {
      return NextResponse.json({ error: 'Missing refresh_token' }, { status: 400 });
    }

    const payload = verifyToken(refresh_token);
    if (!payload || payload.type !== 'refresh') {
      return NextResponse.json({ error: 'Invalid refresh token' }, { status: 401 });
    }

    const accessToken = createToken(
      { deviceId: payload.deviceId, nickname: payload.nickname || null, type: 'access' },
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
