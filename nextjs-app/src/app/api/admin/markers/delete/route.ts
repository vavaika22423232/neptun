import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { loadMessages, saveMessages } from '@/lib/admin/data';

export async function POST(request: Request) {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  try {
    const body = await request.json();
    const { id, lat, lng, text } = body;

    if (!id && (lat === undefined || lng === undefined)) {
      return NextResponse.json({ error: 'Missing id or coordinates' }, { status: 400 });
    }

    const messages = loadMessages();

    // Try matching by id first, then by lat+lng+text
    const filtered = messages.filter(m => {
      // Match by id if provided and message has id
      if (id && m.id && String(m.id) === String(id)) return false;

      // Match by coordinates + text (fallback for messages without id)
      if (lat !== undefined && lng !== undefined) {
        const latMatch = Math.abs(Number(m.lat) - Number(lat)) < 0.0001;
        const lngMatch = Math.abs(Number(m.lng) - Number(lng)) < 0.0001;
        if (latMatch && lngMatch) {
          // If text is provided, also match on text for extra precision
          if (text) {
            const msgText = String(m.text || '').substring(0, 80);
            const reqText = String(text).substring(0, 80);
            if (msgText === reqText) return false;
          } else {
            return false; // coordinates match, no text filter
          }
        }
      }

      return true; // keep this message
    });

    if (filtered.length === messages.length) {
      return NextResponse.json({ error: 'Marker not found' }, { status: 404 });
    }

    saveMessages(filtered);
    return NextResponse.json({ status: 'ok', removed: messages.length - filtered.length });
  } catch (err) {
    console.error('[ADMIN DELETE MARKER]', err);
    return NextResponse.json({ error: 'Failed to delete marker' }, { status: 500 });
  }
}
