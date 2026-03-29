import { NextResponse } from 'next/server';
import { broadcastSSE } from '@/app/api/chat/stream/route';
import {
  addMarker,
  upsertByTrackId,
  beginMarkerIngestBatch,
  endMarkerIngestBatch,
  initStore,
} from '@/lib/markers-store';
import { ingestBodyTooLargeResponse } from '@/lib/ingest-body-limit';
import { validateIngestMarker } from '@/lib/ingest-validate';
import { verifyIngestOrRespond } from '@/lib/ingest-auth-guard';

const MAX_BATCH = 40;

/**
 * POST /api/ingest/batch
 * Body: { markers: Record<string, unknown>[] }
 * Auth: X-Auth-Secret (same as /api/ingest)
 *
 * Used by the Python worker retry queue to drain many pending markers in one
 * HTTP round-trip. Per-marker SSE is suppressed; a single `markers_refresh`
 * event tells clients to refetch /api/data (debounced in useMarkers).
 */
export async function POST(request: Request) {
  const denied = await verifyIngestOrRespond(request);
  if (denied) return denied;

  const tooLarge = ingestBodyTooLargeResponse(request);
  if (tooLarge) return tooLarge;

  await initStore();

  let body: { markers?: unknown[] };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 });
  }

  const raw = body.markers;
  if (!Array.isArray(raw)) {
    return NextResponse.json({ error: 'Expected markers array' }, { status: 400 });
  }

  const slice = raw.slice(0, MAX_BATCH);
  const results: { ok: boolean; error?: string }[] = [];

  const useBatchPersist = slice.length > 0;
  if (useBatchPersist) {
    beginMarkerIngestBatch();
  }
  try {
    for (const item of slice) {
      const marker = item as Record<string, unknown> | null;
      try {
        if (!marker || marker.lat == null || marker.lng == null) {
          results.push({ ok: false, error: 'missing marker or coordinates' });
          continue;
        }
        const v = validateIngestMarker(marker);
        if (!v.ok) {
          results.push({ ok: false, error: v.error });
          continue;
        }
        if (marker.track_id && typeof marker.track_id === 'string') {
          await upsertByTrackId(marker.track_id as string, marker);
        } else {
          await addMarker(marker, { broadcast: false });
        }
        results.push({ ok: true });
      } catch (e) {
        results.push({
          ok: false,
          error: e instanceof Error ? e.message : 'ingest error',
        });
      }
    }
  } finally {
    if (useBatchPersist) {
      await endMarkerIngestBatch();
    }
  }

  const accepted = results.filter((r) => r.ok).length;
  if (accepted > 0) {
    broadcastSSE({
      type: 'markers_refresh',
      data: { batch: true, count: accepted },
    });
  }

  return NextResponse.json({
    ok: true,
    results,
    accepted,
    failed: results.length - accepted,
  });
}
