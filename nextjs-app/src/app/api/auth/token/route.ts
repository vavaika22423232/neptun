import { NextResponse } from 'next/server';
import crypto from 'crypto';

const JWT_SECRET = process.env.AUTH_SECRET || 'default-secret';
const ACCESS_TTL = 3600;  // 1 hour
const REFRESH_TTL = 86400 * 30; // 30 days

function createToken(payload: Record<string, unknown>, expiresIn: number): string {
  const header = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).toString('base64url');
  const now = Math.floor(Date.now() / 1000);
  const body = Buffer.from(JSON.stringify({ ...payload, iat: now, exp: now + expiresIn })).toString('base64url');
  const signature = crypto.createHmac('sha256', JWT_SECRET).update(`${header}.${body}`).digest('base64url');
  return `${header}.${body}.${signature}`;
}

/**
 * POST /api/auth/token
 * Issue JWT access + refresh tokens for a device.
 */
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { deviceId, nickname } = body;

    if (!deviceId) {
      return NextResponse.json({ error: 'Missing deviceId' }, { status: 400 });
    }

    const accessToken = createToken({ deviceId, nickname: nickname || null, type: 'access' }, ACCESS_TTL);
    const refreshToken = createToken({ deviceId, type: 'refresh' }, REFRESH_TTL);

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
