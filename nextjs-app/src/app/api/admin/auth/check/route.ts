import { NextResponse } from 'next/server';
import { cookies, headers } from 'next/headers';
import { validateSession, SESSION_COOKIE_NAME } from '@/lib/admin/auth';
import { getAdminHeaderSecret, safeCompare } from '@/lib/server-secrets';

export async function GET() {
  const adminSecret = getAdminHeaderSecret();
  const headerStore = await headers();
  const secretHeader = headerStore.get('x-auth-secret') || '';
  if (adminSecret && secretHeader && safeCompare(secretHeader, adminSecret)) {
    return NextResponse.json({ authenticated: true });
  }

  const cookieStore = await cookies();
  const token = cookieStore.get(SESSION_COOKIE_NAME)?.value;
  const valid = await validateSession(token);
  return NextResponse.json({ authenticated: valid });
}
