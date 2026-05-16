import { NextResponse } from 'next/server';
import { broadcastSSE } from '@/lib/chat-sse-stream';
import { verifyIngestOrRespond } from '@/lib/ingest-auth-guard';
import { clearTrackedTargetsByRegion, initTargetStore, syncTargetStoreFromRedis } from '@/lib/tracked-target-store';

/**
 * POST /api/ingest/clear-region
 * Body: { region: string, threat_types?: string[], place_contains?: string }
 * Removes all markers in the given oblast, optionally filtered by threat types
 * and/or substring match on place/location (e.g. Kherson channel all-clear for one microdistrict).
 * Called by the worker on allclear / дорозвідка events.
 *
 * Behavior vs TTL: this is immediate removal for matching rows, not wait-for-expiry.
 * See `docs/ALLCLEAR_AND_PUBLIC_MAP.md`.
 */
export async function POST(request: Request) {
  const denied = await verifyIngestOrRespond(request);
  if (denied) return denied;

  let body: { region?: string; threat_types?: string[]; place_contains?: string };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 });
  }

  const { region, threat_types, place_contains } = body;
  if (!region || typeof region !== 'string') {
    return NextResponse.json({ error: 'Missing region' }, { status: 400 });
  }

  const placeContains =
    typeof place_contains === 'string' && place_contains.trim().length > 0
      ? place_contains.trim()
      : undefined;

  await initTargetStore();
  await syncTargetStoreFromRedis();
  const targetsLost = await clearTrackedTargetsByRegion(region, threat_types, placeContains);

  if (targetsLost > 0) {
    broadcastSSE({ type: 'markers_refresh', data: { cleared_region: region, targets_lost: targetsLost } });

    console.log(
      `[CLEAR-REGION] Cleared ${targetsLost} tracks in ${region}` +
      (threat_types ? ` (types: ${threat_types.join(', ')})` : '') +
      (placeContains ? ` (place ~ "${placeContains}")` : '')
    );
  }

  return NextResponse.json({ ok: true, removed: targetsLost, targets_lost: targetsLost });
}
