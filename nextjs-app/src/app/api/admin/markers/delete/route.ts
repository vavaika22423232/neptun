import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { loadHidden, saveHidden } from '@/lib/admin/data';
import { invalidateMarkerDerivedCaches } from '@/lib/cache';
import { broadcastSSE } from '@/lib/chat-sse-stream';
import { initTargetStore, markTrackedTargetLifecycle, syncTargetStoreFromRedis, getTrackedTargetRecords } from '@/lib/tracked-target-store';

function rememberHiddenMarker(marker: { lat?: unknown; lng?: unknown; text?: unknown; manual?: unknown }): string | null {
  const lat = Number(marker.lat);
  const lng = Number(marker.lng);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;

  const source = marker.manual ? 'manual' : 'auto';
  const key = `${lat},${lng}|${marker.text || ''}|${source}`;
  const hidden = loadHidden();
  if (!hidden.includes(key)) {
    hidden.push(key);
    saveHidden(hidden);
    invalidateMarkerDerivedCaches();
  }
  return key;
}

export async function POST(request: Request) {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  try {
    await initTargetStore();
    await syncTargetStoreFromRedis();
    const body = await request.json();
    const { id, lat, lng, text } = body;

    if (!id && (lat === undefined || lng === undefined)) {
      return NextResponse.json({ error: 'Missing id or coordinates' }, { status: 400 });
    }

    const messages = getTrackedTargetRecords();
    const requestedId = id ? String(id) : '';
    const cleanRequestedId = requestedId.replace(/_\d+$/, '');
    const idMatch = requestedId
      ? messages.find((m) => {
          const mid = String(m.id || '');
          const tid = String(m.track_id || '');
          return mid === requestedId || tid === requestedId || mid === cleanRequestedId || tid === cleanRequestedId;
        })
      : undefined;

    const hiddenKey = rememberHiddenMarker({
      lat: lat ?? idMatch?.lat,
      lng: lng ?? idMatch?.lng,
      text: text ?? idMatch?.text,
      manual: idMatch?.manual,
    });

    if (id) {
      const ok = await markTrackedTargetLifecycle(requestedId, 'DESTROYED') ||
                 (cleanRequestedId !== requestedId ? await markTrackedTargetLifecycle(cleanRequestedId, 'DESTROYED') : false);
      
      if (ok) {
        broadcastSSE({ type: 'markers_refresh', data: { reason: 'admin_delete', hidden: Boolean(hiddenKey) } });
        return NextResponse.json({ status: 'ok', removed: 1, hidden: Boolean(hiddenKey) });
      }
    }

    if (lat !== undefined && lng !== undefined) {
      const coordTolerance = 0.05;
      const match = messages.find(m => {
        const latMatch = Math.abs(Number(m.lat) - Number(lat)) < coordTolerance;
        const lngMatch = Math.abs(Number(m.lng) - Number(lng)) < coordTolerance;
        return latMatch && lngMatch;
      });

      if (match) {
        const targetId = String(match.track_id || match.id);
        const ok = await markTrackedTargetLifecycle(targetId, 'DESTROYED');
        if (ok) {
          broadcastSSE({ type: 'markers_refresh', data: { reason: 'admin_delete', hidden: Boolean(hiddenKey) } });
          return NextResponse.json({ status: 'ok', removed: 1, hidden: Boolean(hiddenKey) });
        }
      }
    }

    if (hiddenKey) {
      broadcastSSE({ type: 'markers_refresh', data: { reason: 'admin_delete', hidden: true } });
      return NextResponse.json({ status: 'ok', removed: 0, hidden: true });
    }

    return NextResponse.json({ error: 'Marker not found' }, { status: 404 });
  } catch (err) {
    console.error('[ADMIN DELETE MARKER]', err);
    return NextResponse.json({ error: 'Failed to delete marker' }, { status: 500 });
  }
}
