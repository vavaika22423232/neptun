import crypto from 'crypto';
import { NextResponse } from 'next/server';
import { getJwtSecret } from './server-secrets';
import { resolveChatDisplayNickname } from './chat-nicknames';

export interface ChatIdentity {
  deviceId: string;
  nickname: string;
  isLegacy: boolean;
  type: 'access' | 'legacy' | 'none';
}

export function verifyChatToken(token: string | null, secret: string): ChatIdentity | null {
  if (!token) return null;
  try {
    const [hBase64, pBase64, signature] = token.split('.');
    if (!hBase64 || !pBase64 || !signature) return null;
    
    const data = `${hBase64}.${pBase64}`;
    const expectedSig = crypto.createHmac('sha256', secret).update(data).digest('base64url');
    if (signature !== expectedSig) return null;
    
    const payload = JSON.parse(Buffer.from(pBase64, 'base64url').toString('utf-8'));
    if (Date.now() / 1000 > payload.exp) return null;

    const deviceId = String(payload.deviceId ?? '').trim();
    if (!deviceId) return null;

    const rawNick = payload.nickname;
    const nickname =
      typeof rawNick === 'string' && rawNick.trim().length > 0
        ? rawNick.trim()
        : 'Анонім';

    return {
      deviceId,
      nickname,
      isLegacy: false,
      type: payload.type || 'access',
    };
  } catch { return null; }
}

/**
 * Extract Bearer token from Authorization header or ?token= query param (for SSE).
 */
export function extractToken(request: Request): string | null {
  const auth = request.headers.get('Authorization') || '';
  const bearer = auth.split(' ')[1];
  if (bearer) return bearer;

  try {
    const url = new URL(request.url);
    return url.searchParams.get('token');
  } catch { return null; }
}

/**
 * Require a valid JWT for chat endpoints.
 * Returns the identity or a 401 Response.
 */
export function requireChatAuth(request: Request): ChatIdentity | Response {
  const token = extractToken(request);
  const secret = getJwtSecret();
  if (!secret) {
    return NextResponse.json({ error: 'Server misconfigured' }, { status: 500 });
  }
  const identity = verifyChatToken(token, secret);
  if (!identity) {
    return NextResponse.json(
      { error: 'Потрібна авторизація. Отримайте токен: POST /api/auth/token' },
      { status: 401 },
    );
  }
  const nickname = resolveChatDisplayNickname(identity.deviceId, identity.nickname);
  return { ...identity, nickname };
}
