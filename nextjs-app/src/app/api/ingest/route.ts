import { NextResponse } from 'next/server';
import { broadcastSSE } from '@/lib/chat-sse-stream';
import { addMarker, patchMarker, upsertByTrackId, initStore, getRawMessages } from '@/lib/markers-store';
import { attachDisplayPolicyToPayload } from '@/lib/marker-broadcast-enrich';
import { loadSettings } from '@/lib/admin/data';
import { ingestBodyTooLargeResponse } from '@/lib/ingest-body-limit';
import { validateIngestMarker, validateIngestPatchUpdates } from '@/lib/ingest-validate';
import { verifyIngestOrRespond } from '@/lib/ingest-auth-guard';
import { IngestMarkerSchema, IngestCandidateEventSchema, IngestPatchSchema } from '@/lib/api-schemas';
import { ingestShouldBroadcastMarker } from '@/lib/marker-publication';
import { normalizeAirBalloonThreatType } from '@/lib/threat-type-air-balloon';
import { ingestMarkerEvidence, initTargetStore, syncTargetStoreFromRedis, trackerDecisionToPublicRecord } from '@/lib/tracked-target-store';

/** Convert candidate_event payload (worker V2 format) to flat marker record */
function candidateEventToMarker(ce: Record<string, unknown>): Record<string, unknown> {
  const loc = (ce.locality ?? {}) as Record<string, unknown>;
  return {
    ...ce,
    id: ce.event_id ?? ce.fingerprint,
    track_id: ce.target_id ?? ce.event_id,
    lat: loc.lat ?? ce.lat,
    lng: loc.lng ?? ce.lng,
    place: loc.place ?? ce.place,
    region: loc.region ?? ce.region,
    confidence: loc.confidence ?? ce.confidence,
    geocode_tier: loc.geocode_tier ?? ce.geocode_tier,
    resolve_status: loc.resolve_status ?? ce.resolve_status,
    threat_type: ce.threat_type,
    text: ce.raw_text,
    channel: ce.channel_name ?? ce.source,
    date: typeof ce.ts === 'number' ? new Date(ce.ts * 1000).toISOString() : ce.ts,
  };
}

// ── POST handler ─────────────────────────────────────────────────────────────

export async function POST(request: Request) {
  const denied = await verifyIngestOrRespond(request);
  if (denied) return denied;

  const tooLarge = ingestBodyTooLargeResponse(request);
  if (tooLarge) return tooLarge;

  await initStore();
  await initTargetStore();
  await syncTargetStoreFromRedis();

  let rawBody: unknown;
  try {
    rawBody = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 });
  }

  // Support both {marker:{...}} and {candidate_event:{...}} (worker V2 format)
  let marker: Record<string, unknown>;
  const candidateParsed = IngestCandidateEventSchema.safeParse(rawBody);
  if (candidateParsed.success) {
    marker = candidateEventToMarker(candidateParsed.data.candidate_event as Record<string, unknown>);
  } else {
    const parsed = IngestMarkerSchema.safeParse(rawBody);
    if (!parsed.success) {
      return NextResponse.json({ error: parsed.error.issues[0]?.message || 'Invalid payload' }, { status: 400 });
    }
    marker = parsed.data.marker as Record<string, unknown>;
  }

  normalizeAirBalloonThreatType(marker);


  const coordCheck = validateIngestMarker(marker);
  if (!coordCheck.ok) {
    console.warn(`[INGEST] Rejected marker coords: ${coordCheck.error}`, marker.id ?? marker.track_id);
    return NextResponse.json({ error: coordCheck.error }, { status: 400 });
  }

  // --- V3 Tracking Engine Ingest ---
  const trackerDecision = await ingestMarkerEvidence(marker);
  const publicV3Marker = trackerDecisionToPublicRecord(trackerDecision);

  // --- Legacy Store Ingest ---
  let finalResult: { id?: string; total: number; removed?: number; mode?: 'created' | 'updated' };
  let shouldBroadcast = false;

  if (marker.track_id && typeof marker.track_id === 'string') {
    const upsertRes = await upsertByTrackId(marker.track_id, marker);
    finalResult = upsertRes;
    const rowsAfter = getRawMessages();
    const fullRowForBroadcast =
      rowsAfter.find(
        (r) => String(r.track_id) === String(marker.track_id) && String(r.id) === String(upsertRes.id),
      ) ??
      rowsAfter.find((r) => String(r.track_id) === String(marker.track_id));
    
    shouldBroadcast = ingestShouldBroadcastMarker(
      (fullRowForBroadcast ?? marker) as Record<string, unknown>,
    );

    if (shouldBroadcast) {
      const broadcastMarker: Record<string, unknown> = { ...marker, id: upsertRes.id };
      if (upsertRes.mode === 'updated') {
        delete broadcastMarker.positions;
      }
      broadcastSSE({
        type: 'track_update',
        data: { track_id: String(marker.track_id), mode: upsertRes.mode, marker: broadcastMarker },
      });
    }
  } else {
    const addRes = await addMarker(marker);
    finalResult = addRes;
    const resolvedId = addRes.id || (marker.id as string);
    const fullRowLegacy = getRawMessages().find((r) => String(r.id) === String(resolvedId));
    shouldBroadcast = ingestShouldBroadcastMarker(
      (fullRowLegacy ?? marker) as Record<string, unknown>,
    );

    if (shouldBroadcast) {
      broadcastSSE({ type: 'marker_created', data: { ...marker, id: resolvedId } });
    }
  }

  // --- Admin Feed Broadcast ---
  broadcastSSE({
    type: 'admin_feed',
    data: {
      ...marker,
      status: 'processed',
      track_id: marker.track_id || (trackerDecision as any)?.target?.id,
      v3_action: (trackerDecision as any)?.action,
      v3_lifecycle: (trackerDecision as any)?.target?.lifecycle_state
    }
  });

  // --- V3 Broadcast (if V3 thinks it's public but legacy logic didn't already send it) ---
  if (publicV3Marker && !shouldBroadcast) {
     broadcastSSE({ type: 'marker_created', data: publicV3Marker });
  }

  return NextResponse.json({
    ok: true,
    total: finalResult.total,
    id: finalResult.id ?? marker.id,
    public_broadcast: shouldBroadcast || !!publicV3Marker,
    v3_status: trackerDecision?.action
  });
}

// ── PATCH handler — update existing marker fields ────────────────────────────

export async function PATCH(request: Request) {
  const denied = await verifyIngestOrRespond(request);
  if (denied) return denied;

  const tooLargePatch = ingestBodyTooLargeResponse(request);
  if (tooLargePatch) return tooLargePatch;

  await initStore();

  let rawBody: unknown;
  try {
    rawBody = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 });
  }

  const parsedPatch = IngestPatchSchema.safeParse(rawBody);
  if (!parsedPatch.success) {
    return NextResponse.json({ error: parsedPatch.error.issues[0]?.message || 'Invalid payload' }, { status: 400 });
  }

  const { id, updates } = parsedPatch.data;

  const patchCoords = validateIngestPatchUpdates(updates);
  if (!patchCoords.ok) {
    console.warn(`[INGEST] PATCH rejected: ${patchCoords.error}`);
    return NextResponse.json({ error: patchCoords.error }, { status: 400 });
  }

  const ok = await patchMarker(id, updates);
  if (!ok) {
    return NextResponse.json({ error: 'Marker not found' }, { status: 404 });
  }

  const trackId = updates.track_id as string | undefined;
  const fullRowAfterPatch =
    getRawMessages().find((r) => String(r.id) === id) ??
    (trackId ? getRawMessages().find((r) => String(r.track_id) === trackId) : undefined);
  const minConfPatch = loadSettings().minConfidence ?? 0.65;
  const shouldPatchBroadcast =
    fullRowAfterPatch &&
    ingestShouldBroadcastMarker(fullRowAfterPatch as Record<string, unknown>);

  if (shouldPatchBroadcast) {
    if (trackId) {
      const broadcastMarker: Record<string, unknown> = { id, ...updates };
      attachDisplayPolicyToPayload(fullRowAfterPatch as Record<string, unknown>, broadcastMarker);
      broadcastSSE({
        type: 'track_update',
        data: { track_id: trackId, mode: 'updated', marker: broadcastMarker },
      });
    } else {
      broadcastSSE({ type: 'marker_update', data: { id, ...updates } });
    }
  }

  console.log(`[INGEST] PATCH marker ${id}: ${Object.keys(updates).join(', ')}`);
  return NextResponse.json({ ok: true, updated: id });
}
