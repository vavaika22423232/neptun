import { NextResponse } from 'next/server';
import { broadcastSSE } from '@/app/api/chat/stream/route';
import { deleteByRegion, initStore } from '@/lib/markers-store';
import { verifyIngestOrRespond } from '@/lib/ingest-auth-guard';

/**
 * POST /api/ingest/clear-region
 * Body: { region: string, threat_types?: string[] }
 * Removes all markers in the given oblast, optionally filtered by threat types.
 * Called by the worker on allclear / дорозвідка events.
 */
export async function POST(request: Request) {
  const denied = await verifyIngestOrRespond(request);
  if (denied) return denied;

  let body: { region?: string; threat_types?: string[] };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 });
  }

  const { region, threat_types } = body;
  if (!region || typeof region !== 'string') {
    return NextResponse.json({ error: 'Missing region' }, { status: 400 });
  }

  await initStore();
  const removed = await deleteByRegion(region, threat_types);

  if (removed > 0) {
    // Broadcast marker_new to trigger client refetch (cleared markers will be gone)
    broadcastSSE({ type: 'marker_new', data: { cleared_region: region, removed } });

    console.log(
      `[CLEAR-REGION] Removed ${removed} markers in ${region}` +
      (threat_types ? ` (types: ${threat_types.join(', ')})` : '')
    );
  }

  return NextResponse.json({ ok: true, removed });
}
