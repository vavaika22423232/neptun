import { NextResponse } from 'next/server';
import { broadcastSSE } from '@/lib/chat-sse-stream';
import {
  addMarker,
  upsertByTrackId,
  beginMarkerIngestBatch,
  endMarkerIngestBatch,
  getRawMessages,
  initStore,
} from '@/lib/markers-store';
import { ingestBodyTooLargeResponse } from '@/lib/ingest-body-limit';
import { validateIngestMarker } from '@/lib/ingest-validate';
import { verifyIngestOrRespond } from '@/lib/ingest-auth-guard';
import { IngestMarkerSchema } from '@/lib/api-schemas';
import { normalizeAirBalloonThreatType } from '@/lib/threat-type-air-balloon';
import { normalizeIngestMotionFields } from '@/lib/ingest-motion-normalize';
import { assertAirAlarmGateForIngest } from '@/lib/ingest-air-alarm-gate';
import { computeMarkerEventFingerprint } from '@/lib/public-marker-policy';
import { ingestMarkerEvidence, trackerDecisionToPublicRecord } from '@/lib/tracked-target-store';
import { ingestShouldBroadcastMarker } from '@/lib/marker-publication';

function normalizeServerTargetMetadata(marker: Record<string, unknown>): void {
  if (marker.manual === true) {
    marker.target_lifecycle_state = 'CONFIRMED';
    marker.target_confidence = 1;
    marker.source_count = 1;
    return;
  }
  if (!marker.track_id || typeof marker.track_id !== 'string') {
    marker.track_id = `pending_${String(marker.event_fingerprint || computeMarkerEventFingerprint(marker)).slice(0, 16)}`;
  }
  if (!marker.target_lifecycle_state) marker.target_lifecycle_state = 'DETECTED';
  if (typeof marker.target_confidence !== 'number') {
    const c = typeof marker.confidence === 'number' ? marker.confidence : 0.5;
    marker.target_confidence = Math.min(1, Math.max(0, c));
  }
  if (typeof marker.source_count !== 'number') marker.source_count = 1;
}

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
  const results: { ok: boolean; error?: string; code?: string }[] = [];
  let publicChanged = 0;

  const useBatchPersist = slice.length > 0;
  if (useBatchPersist) {
    beginMarkerIngestBatch();
  }
  try {
    for (const item of slice) {
      try {
        const parsed = IngestMarkerSchema.safeParse({ marker: item });
        if (!parsed.success) {
          results.push({ ok: false, error: parsed.error.issues[0]?.message || 'Invalid payload' });
          continue;
        }
        const marker = parsed.data.marker as Record<string, unknown>;
        normalizeAirBalloonThreatType(marker);
        normalizeIngestMotionFields(marker);
        marker.event_fingerprint = computeMarkerEventFingerprint(marker);
        normalizeServerTargetMetadata(marker);
        if (!marker || marker.lat == null || marker.lng == null) {
          results.push({ ok: false, error: 'missing marker or coordinates' });
          continue;
        }
        const v = validateIngestMarker(marker);
        if (!v.ok) {
          results.push({ ok: false, error: v.error });
          continue;
        }
        const airGate = await assertAirAlarmGateForIngest(marker);
        if (!airGate.ok) {
          results.push({
            ok: false,
            error: airGate.reason,
            code: 'INGEST_POLICY_REJECT',
          });
          continue;
        }
        if (getRawMessages().some((m) => String(m.event_fingerprint || '') === marker.event_fingerprint)) {
          results.push({ ok: true, code: 'DUPLICATE_REPLAY' });
          continue;
        }
        if (marker.track_id && typeof marker.track_id === 'string') {
          await upsertByTrackId(marker.track_id as string, marker);
        } else {
          await addMarker(marker, { broadcast: false });
        }
        const trackerDecision = await ingestMarkerEvidence(marker);
        const trackedRecord = trackerDecisionToPublicRecord(trackerDecision);
        if (trackedRecord && ingestShouldBroadcastMarker(trackedRecord)) {
          publicChanged += 1;
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
  const acceptedNew = results.filter((r) => r.ok && r.code !== 'DUPLICATE_REPLAY').length;
  if (publicChanged > 0) {
    broadcastSSE({
      type: 'markers_refresh',
      data: { batch: true, count: publicChanged },
    });
  }

  return NextResponse.json({
    ok: true,
    results,
    accepted,
    accepted_new: acceptedNew,
    public_changed: publicChanged,
    failed: results.length - accepted,
  });
}
