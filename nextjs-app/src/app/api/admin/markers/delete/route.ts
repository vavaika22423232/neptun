import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { loadMessages, saveMessages } from '@/lib/admin/data';

export async function POST(request: Request) {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  try {
    const body = await request.json();
    const { id } = body;

    if (!id) return NextResponse.json({ error: 'Missing id' }, { status: 400 });

    const messages = loadMessages();
    const filtered = messages.filter(m => m.id !== id);

    if (filtered.length === messages.length) {
      return NextResponse.json({ error: 'Marker not found' }, { status: 404 });
    }

    saveMessages(filtered);
    return NextResponse.json({ status: 'ok', deleted: id });
  } catch (err) {
    console.error('[ADMIN DELETE MARKER]', err);
    return NextResponse.json({ error: 'Failed to delete marker' }, { status: 500 });
  }
}
