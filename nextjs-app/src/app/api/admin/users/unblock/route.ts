import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { loadBlocked, saveBlocked } from '@/lib/admin/data';

export async function POST(request: Request) {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  try {
    const body = await request.json();
    const { id } = body;
    if (!id) return NextResponse.json({ error: 'Missing id' }, { status: 400 });

    const blocked = loadBlocked();
    const updated = blocked.filter(b => b !== String(id));
    saveBlocked(updated);

    return NextResponse.json({ status: 'ok' });
  } catch (err) {
    console.error('[ADMIN UNBLOCK]', err);
    return NextResponse.json({ error: 'Failed to unblock user' }, { status: 500 });
  }
}
