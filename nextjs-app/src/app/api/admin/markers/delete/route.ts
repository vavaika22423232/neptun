import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { deleteMarker, getRawMessages, initStore } from '@/lib/markers-store';

export async function POST(request: Request) {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  try {
    await initStore();
    const body = await request.json();
    const { id, lat, lng, text } = body;

    if (!id && (lat === undefined || lng === undefined)) {
      return NextResponse.json({ error: 'Missing id or coordinates' }, { status: 400 });
    }

    // Try delete by id first
    if (id) {
      // The frontend appends _0, _1, etc., for grouped markers (count > 1).
      // We try exact match first, then fallback to original base ID.
      const cleanId = String(id).replace(/_\d+$/, '');
      let ok = await deleteMarker(String(id));
      if (!ok && cleanId !== String(id)) {
        ok = await deleteMarker(cleanId);
      }
      if (ok) {
        return NextResponse.json({ status: 'ok', removed: 1 });
      }
    }

    // Fallback: find by coordinates (ticker moves markers — use ~1km tolerance)
    if (lat !== undefined && lng !== undefined) {
      const messages = getRawMessages();
      const coordTolerance = 0.05; // ~5km — ticker moves markers continuously
      const match = messages.find(m => {
        const latMatch = Math.abs(Number(m.lat) - Number(lat)) < coordTolerance;
        const lngMatch = Math.abs(Number(m.lng) - Number(lng)) < coordTolerance;
        if (!latMatch || !lngMatch) return false;
        if (text) {
          // Bulletproof check: strip ALL invisible/special Telegram characters, keep only alphanumerics
          const cleanRegex = /[^a-zA-Zа-яА-ЯіІїЇєЄ0-9]/g;
          const msgText = String(m.text || '').replace(cleanRegex, '').toLowerCase().substring(0, 30);
          const reqText = String(text).replace(cleanRegex, '').toLowerCase().substring(0, 30);
          return msgText.includes(reqText) || reqText.includes(msgText);
        }
        return true;
      });

      if (match) {
        const targetId = match.id || match.track_id;
        if (targetId) {
          const ok = await deleteMarker(String(targetId));
          if (ok) {
            return NextResponse.json({ status: 'ok', removed: 1 });
          }
        }
      }
    }

    return NextResponse.json({ error: 'Marker not found' }, { status: 404 });
  } catch (err) {
    console.error('[ADMIN DELETE MARKER]', err);
    return NextResponse.json({ error: 'Failed to delete marker' }, { status: 500 });
  }
}
