import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { loadMessages, saveMessages } from '@/lib/admin/data';

export async function POST(request: Request) {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  try {
    const body = await request.json();
    const { id, ...updates } = body;

    if (!id) return NextResponse.json({ error: 'Missing id' }, { status: 400 });

    if (updates.lat !== undefined && (updates.lat < 43 || updates.lat > 53.8)) {
      return NextResponse.json({ error: 'Invalid lat' }, { status: 400 });
    }
    if (updates.lng !== undefined && (updates.lng < 21 || updates.lng > 41.5)) {
      return NextResponse.json({ error: 'Invalid lng' }, { status: 400 });
    }

    const messages = loadMessages();
    const idx = messages.findIndex(m => m.id === id);
    if (idx === -1) return NextResponse.json({ error: 'Marker not found' }, { status: 404 });

    // Apply updates
    for (const [key, value] of Object.entries(updates)) {
      messages[idx][key] = value;
    }

    saveMessages(messages);
    return NextResponse.json({ status: 'ok', marker: messages[idx] });
  } catch (err) {
    console.error('[ADMIN UPDATE MARKER]', err);
    return NextResponse.json({ error: 'Failed to update marker' }, { status: 500 });
  }
}
