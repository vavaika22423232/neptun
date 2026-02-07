import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { verifyPassword, createSessionToken, SESSION_COOKIE_NAME, sessionCookieOptions } from '@/lib/admin/auth';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const password = (body.password || '').trim();

    if (!verifyPassword(password)) {
      return NextResponse.json({ status: 'error', error: 'Invalid password' }, { status: 401 });
    }

    const token = createSessionToken();
    const cookieStore = await cookies();
    cookieStore.set(SESSION_COOKIE_NAME, token, sessionCookieOptions);

    return NextResponse.json({ status: 'ok' });
  } catch {
    return NextResponse.json({ status: 'error', error: 'Invalid request' }, { status: 400 });
  }
}
