import { NextResponse } from 'next/server';
import { cookies, headers } from 'next/headers';
import {
  createSessionToken,
  SESSION_COOKIE_NAME,
  sessionCookieOptions,
  validateSession,
} from '@/lib/admin/auth';
import { getAdminHeaderSecret, safeCompare } from '@/lib/server-secrets';

function resolveNextPath(raw: string | null): string {
  if (!raw) return '/?embed=1';
  if (!raw.startsWith('/')) return '/?embed=1';
  if (raw.startsWith('//')) return '/?embed=1';
  return raw;
}

export async function GET(request: Request) {
  const url = new URL(request.url);
  const nextPath = resolveNextPath(url.searchParams.get('next'));
  const redirectUrl = new URL(nextPath, url.origin);

  const cookieStore = await cookies();
  const existing = cookieStore.get(SESSION_COOKIE_NAME)?.value;
  if (await validateSession(existing)) {
    return NextResponse.redirect(redirectUrl);
  }

  const adminSecret = getAdminHeaderSecret();
  const headerStore = await headers();
  const secretHeader = headerStore.get('x-auth-secret') || '';
  if (!adminSecret || !secretHeader || !safeCompare(secretHeader, adminSecret)) {
    return NextResponse.json({ error: 'Not authenticated' }, { status: 401 });
  }

  const token = await createSessionToken();
  if (!token) {
    return NextResponse.json({ error: 'Session storage unavailable' }, { status: 503 });
  }

  cookieStore.set(SESSION_COOKIE_NAME, token, sessionCookieOptions);
  return NextResponse.redirect(redirectUrl);
}
