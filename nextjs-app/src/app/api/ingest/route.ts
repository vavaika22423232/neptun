import { NextResponse } from 'next/server';
import { broadcastSSE } from '@/lib/chat-sse-stream';
import { addMarker, patchMarker, upsertByTrackId, initStore, getRawMessages } from '@/lib/markers-store';
import { attachDisplayPolicyToPayload } from '@/lib/marker-broadcast-enrich';
import { loadSettings } from '@/lib/admin/data';
import { ingestBodyTooLargeResponse } from '@/lib/ingest-body-limit';
import { validateIngestMarker, validateIngestPatchUpdates } from '@/lib/ingest-validate';
import { verifyIngestOrRespond } from '@/lib/ingest-auth-guard';
import { IngestMarkerSchema, IngestPatchSchema } from '@/lib/api-schemas';
import { ingestShouldBroadcastMarker } from '@/lib/ingest-confidence-gate';

// ── POST handler ─────────────────────────────────────────────────────────────

export async function POST(request: Request) {
  const denied = await verifyIngestOrRespond(request);
  if (denied) return denied;

  const tooLarge = ingestBodyTooLargeResponse(request);
  if (tooLarge) return tooLarge;

  await initStore();

  let rawBody: unknown;
  try {
    rawBody = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 });
  }

  const parsed = IngestMarkerSchema.safeParse(rawBody);
  if (!parsed.success) {
    return NextResponse.json({ error: parsed.error.issues[0]?.message || 'Invalid payload' }, { status: 400 });
  }

  const marker = parsed.data.marker as Record<string, unknown>;

  const coordCheck = validateIngestMarker(marker);
  if (!coordCheck.ok) {
    console.warn(`[INGEST] Rejected marker coords: ${coordCheck.error}`, marker.id ?? marker.track_id);
    return NextResponse.json({ error: coordCheck.error }, { status: 400 });
  }

  // Track-aware upsert: if marker has track_id, use upsert logic
  if (marker.track_id && typeof marker.track_id === 'string') {
    const result = await upsertByTrackId(marker.track_id, marker);

    const minConf = loadSettings().minConfidence ?? 0.65;
    const rowsAfter = getRawMessages();
    const fullRowForBroadcast =
      rowsAfter.find(
        (r) => String(r.track_id) === String(marker.track_id) && String(r.id) === String(result.id),
      ) ??
      rowsAfter.find((r) => String(r.track_id) === String(marker.track_id));
    const shouldBroadcast = ingestShouldBroadcastMarker(
      (fullRowForBroadcast ?? marker) as Record<string, unknown>,
      minConf,
    );

    // Broadcast track update — strip positions[] to save bandwidth (skip if below confidence threshold)
    // For 'updated' mode, client appends lat/lng locally; for 'created', client uses initial position
    // Full positions[] is fetched via /api/data polling
    if (shouldBroadcast) {
      const broadcastMarker: Record<string, unknown> = { ...marker, id: result.id };
      if (result.mode === 'updated') {
        delete broadcastMarker.positions; // client builds locally from lat/lng
      } else if (Array.isArray(broadcastMarker.positions) && (broadcastMarker.positions as unknown[]).length > 3) {
        broadcastMarker.positions = (broadcastMarker.positions as unknown[]).slice(-3);
      }
      const tid = String(marker.track_id);
      const fullRow =
        rowsAfter.find((r) => String(r.track_id) === tid && String(r.id) === String(result.id)) ??
        rowsAfter.find((r) => String(r.track_id) === tid);
      if (fullRow && typeof fullRow === 'object') {
        attachDisplayPolicyToPayload(fullRow as Record<string, unknown>, broadcastMarker);
      }
      broadcastSSE({
        type: 'track_update',
        data: {
          track_id: marker.track_id,
          mode: result.mode,
          marker: broadcastMarker,
        },
      });
    }

    console.log(
      `[INGEST] Track ${result.mode}: ${marker.track_id} (id=${result.id}) — ${result.total} total`
    );

    return NextResponse.json({ ok: true, total: result.total, mode: result.mode, id: result.id });
  }

  // Legacy: no track_id — add as standalone marker
  const result = await addMarker(marker);

  const minConf = loadSettings().minConfidence ?? 0.65;
  const resolvedId = result.id ?? marker.id;
  const fullRowLegacy = getRawMessages().find((r) => String(r.id) === String(resolvedId));
  const shouldBroadcast = ingestShouldBroadcastMarker(
    (fullRowLegacy ?? marker) as Record<string, unknown>,
    minConf,
  );

  // Broadcast new marker to all SSE clients (real-time push) — skip if below confidence threshold
  if (shouldBroadcast) {
    const payload: Record<string, unknown> = { ...marker };
    const fullRow = fullRowLegacy;
    if (fullRow && typeof fullRow === 'object') {
      attachDisplayPolicyToPayload(fullRow as Record<string, unknown>, payload);
    }
    broadcastSSE({ type: 'marker_new', data: payload });
  }

  console.log(
    `[INGEST] Saved marker ${marker.id} — ${result.total} total` +
    (result.removed > 0 ? `, pruned ${result.removed} old` : '')
  );

  return NextResponse.json({
    ok: true,
    total: result.total,
    id: result.id ?? marker.id,
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
    ingestShouldBroadcastMarker(fullRowAfterPatch as Record<string, unknown>, minConfPatch);

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
