import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { loadHidden, rememberDestroyedTracks, saveHidden } from '@/lib/admin/data';
import { invalidateMarkerDerivedCaches } from '@/lib/cache';
import { broadcastSSE } from '@/lib/chat-sse-stream';
import { deleteMarker, getRawMessages, initStore } from '@/lib/markers-store';
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
    await initStore();
    await initTargetStore();
    await syncTargetStoreFromRedis();
    const body = await request.json();
    const { id, lat, lng, text } = body;

    if (!id && (lat === undefined || lng === undefined)) {
      return NextResponse.json({ error: 'Missing id or coordinates' }, { status: 400 });
    }

    const rawMessages = getRawMessages();
    const trackedMessages = getTrackedTargetRecords();
    const messages = [...rawMessages, ...trackedMessages];
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

    const destroyedIds = [
      requestedId,
      cleanRequestedId,
      idMatch?.id,
      idMatch?.track_id,
    ].filter((v): v is string => typeof v === 'string' && v.length > 0);
    const destroyedRemembered = rememberDestroyedTracks(...destroyedIds);
    if (destroyedRemembered || hiddenKey) {
      invalidateMarkerDerivedCaches();
    }

    if (id) {
      const removedRaw = await deleteMarker(requestedId) ||
        (cleanRequestedId !== requestedId ? await deleteMarker(cleanRequestedId) : false);
      const removedTrack = await markTrackedTargetLifecycle(requestedId, 'DESTROYED') ||
        (cleanRequestedId !== requestedId ? await markTrackedTargetLifecycle(cleanRequestedId, 'DESTROYED') : false);
      
      if (removedRaw || removedTrack || destroyedRemembered) {
        if (removedTrack && !removedRaw) {
          broadcastSSE({ type: 'marker_delete', data: { id: requestedId } });
        } else if (removedRaw) {
          broadcastSSE({ type: 'marker_delete', data: { id: requestedId } });
        }
        broadcastSSE({ type: 'markers_refresh', data: { reason: 'admin_delete', hidden: Boolean(hiddenKey) } });
        return NextResponse.json({
          status: 'ok',
          removed: removedRaw || removedTrack ? 1 : 0,
          hidden: Boolean(hiddenKey),
          destroyed: destroyedRemembered,
        });
      }
    }

    if (!id && lat !== undefined && lng !== undefined) {
      const coordTolerance = 0.05;
      const match = messages.find(m => {
        const latMatch = Math.abs(Number(m.lat) - Number(lat)) < coordTolerance;
        const lngMatch = Math.abs(Number(m.lng) - Number(lng)) < coordTolerance;
        return latMatch && lngMatch;
      });

      if (match) {
        const markerId = String(match.id || '');
        const targetId = String(match.track_id || markerId);
        rememberDestroyedTracks(markerId, targetId);
        const removedRaw = markerId ? await deleteMarker(markerId) : false;
        const removedTrack = targetId ? await markTrackedTargetLifecycle(targetId, 'DESTROYED') : false;
        if (removedRaw || removedTrack) {
          broadcastSSE({ type: 'marker_delete', data: { id: targetId || markerId } });
          broadcastSSE({ type: 'markers_refresh', data: { reason: 'admin_delete', hidden: Boolean(hiddenKey) } });
          return NextResponse.json({ status: 'ok', removed: 1, hidden: Boolean(hiddenKey), destroyed: true });
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
