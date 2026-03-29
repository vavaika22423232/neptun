import { NextResponse } from 'next/server';
import { cookies, headers } from 'next/headers';
import { validateSession, SESSION_COOKIE_NAME } from './auth';
import { getAdminHeaderSecret, safeCompare } from '@/lib/server-secrets';

/** Check admin auth for API routes. Returns null if authorized, or a 401 response. */
export async function requireAdminAuth(): Promise<NextResponse | null> {
  const adminSecret = getAdminHeaderSecret();
  const headerStore = await headers();
  const secretHeader = headerStore.get('x-auth-secret') || '';
  if (adminSecret && secretHeader && safeCompare(secretHeader, adminSecret)) {
    return null;
  }

  const cookieStore = await cookies();
  const token = cookieStore.get(SESSION_COOKIE_NAME)?.value;
  if (!(await validateSession(token))) {
    return NextResponse.json({ status: 'forbidden', error: 'Not authenticated' }, { status: 401 });
  }
  return null;
}
