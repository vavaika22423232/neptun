import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { verifyPassword, createSessionToken, SESSION_COOKIE_NAME, sessionCookieOptions } from '@/lib/admin/auth';
import { redisFixedWindowAllow } from '@/lib/redis-rate-limit';

export async function POST(request: Request) {
  try {
    const clientIP = request.headers.get('X-Real-IP')
      || request.headers.get('X-Forwarded-For')?.split(',')[0]?.trim()
      || 'unknown';

    const ipAllowed = await redisFixedWindowAllow(`rl:admin:login:${clientIP}`, 5, 300, false);
    if (!ipAllowed) {
      return NextResponse.json(
        { status: 'error', error: 'Too many login attempts. Try again in 5 minutes.' },
        { status: 429 },
      );
    }

    const globalAllowed = await redisFixedWindowAllow('rl:admin:login:global', 20, 300, false);
    if (!globalAllowed) {
      return NextResponse.json(
        { status: 'error', error: 'Too many login attempts globally.' },
        { status: 429 },
      );
    }

    const body = await request.json();
    const password = (body.password || '').trim();

    if (!(await verifyPassword(password))) {
      return NextResponse.json({ status: 'error', error: 'Invalid password' }, { status: 401 });
    }

    const token = await createSessionToken();
    if (!token) {
      return NextResponse.json(
        { status: 'error', error: 'Session storage unavailable' },
        { status: 503 },
      );
    }
    const cookieStore = await cookies();
    cookieStore.set(SESSION_COOKIE_NAME, token, sessionCookieOptions);

    return NextResponse.json({ status: 'ok' });
  } catch {
    return NextResponse.json({ status: 'error', error: 'Invalid request' }, { status: 400 });
  }
}
