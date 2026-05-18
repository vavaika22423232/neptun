import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { loadBlocked } from '@/lib/admin/data';

export const dynamic = 'force-dynamic';

export async function GET() {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  try {
    const blocked = loadBlocked();
    return NextResponse.json({ blocked });
  } catch (err) {
    console.error('[ADMIN USERS]', err);
    return NextResponse.json({ error: 'Failed to load users' }, { status: 500 });
  }
}
