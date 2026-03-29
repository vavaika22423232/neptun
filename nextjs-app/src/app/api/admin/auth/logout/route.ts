import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { destroySession, SESSION_COOKIE_NAME } from '@/lib/admin/auth';

export async function POST() {
  const cookieStore = await cookies();
  const token = cookieStore.get(SESSION_COOKIE_NAME)?.value;
  if (token) await destroySession(token);
  cookieStore.delete(SESSION_COOKIE_NAME);
  return NextResponse.json({ status: 'ok' });
}
