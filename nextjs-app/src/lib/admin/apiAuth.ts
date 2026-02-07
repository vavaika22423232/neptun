import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { validateSession, SESSION_COOKIE_NAME } from './auth';

/** Check admin auth for API routes. Returns null if authorized, or a 401 response. */
export async function requireAdminAuth(): Promise<NextResponse | null> {
  const cookieStore = await cookies();
  const token = cookieStore.get(SESSION_COOKIE_NAME)?.value;
  if (!validateSession(token)) {
    return NextResponse.json({ status: 'forbidden', error: 'Not authenticated' }, { status: 401 });
  }
  return null;
}
