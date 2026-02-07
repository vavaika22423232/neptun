import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { loadHidden, saveHidden } from '@/lib/admin/data';

export async function POST(request: Request) {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  try {
    const body = await request.json();
    const { key } = body;

    if (!key) return NextResponse.json({ error: 'Missing key' }, { status: 400 });

    const hidden = loadHidden();
    const updated = hidden.filter(h => h !== key);
    saveHidden(updated);

    return NextResponse.json({ status: 'ok' });
  } catch (err) {
    console.error('[ADMIN UNHIDE]', err);
    return NextResponse.json({ error: 'Failed to unhide marker' }, { status: 500 });
  }
}
