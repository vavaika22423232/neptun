import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { updateTrackedTarget } from '@/lib/tracked-target-store';

export async function POST(request: Request) {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  try {
    const body = await request.json();
    const { id, ...updates } = body;
    if (!id) return NextResponse.json({ error: 'Missing id' }, { status: 400 });
    const updatesRec = updates as Record<string, unknown>;
    const ok = await updateTrackedTarget(String(id), updatesRec);
    if (!ok) return NextResponse.json({ error: 'Track not found' }, { status: 404 });

    return NextResponse.json({ status: 'ok' });
  } catch (err) {
    console.error('[ADMIN UPDATE MARKER]', err);
    return NextResponse.json({ error: 'Failed to update marker' }, { status: 500 });
  }
}
