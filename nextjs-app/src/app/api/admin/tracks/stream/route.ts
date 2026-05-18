/**
 * P4-A: GET /api/admin/tracks/stream
 *
 * Server-Sent Events stream that pushes live tracker snapshots every 3 seconds.
 * Each SSE event includes a JSON payload with the full set of tracked target
 * store records, so admin dashboards can render a real-time tracker view without
 * polling /api/admin/tracks/debug repeatedly.
 *
 * Auth: Admin only (same as other /api/admin/* endpoints).
 */
import { requireAdminAuth } from '@/lib/admin/apiAuth';

export const dynamic = 'force-dynamic';

const PUSH_INTERVAL_MS = 3_000;
const CLIENT_TIMEOUT_MS = 5 * 60_000;

export async function GET(request: Request) {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  const {
    getTrackedTargetRecords,
    initTargetStore,
    syncTargetStoreFromRedis,
    getTrackedTargetsVersion,
  } = await import('@/lib/tracked-target-store');

  await initTargetStore();

  const encoder = new TextEncoder();
  let closed = false;

  request.signal.addEventListener('abort', () => { closed = true; });

  const stream = new ReadableStream({
    async start(controller) {
      const deadline = Date.now() + CLIENT_TIMEOUT_MS;
      let lastVersion = -1;

      const push = async () => {
        if (closed || Date.now() > deadline) {
          try { controller.close(); } catch { /* already closed */ }
          return;
        }

        try {
          await syncTargetStoreFromRedis();
          const ver = getTrackedTargetsVersion();
          const nowMs = Date.now();

          const records = getTrackedTargetRecords();
          const payload = {
            version: ver,
            ts: nowMs,
            count: records.length,
            targets: records.map((r) => ({
              id: r.id,
              track_id: r.track_id,
              lat: r.lat,
              lng: r.lng,
              threat_type: r.threat_type,
              lifecycle: r.target_lifecycle_state,
              confidence: r.target_confidence,
              tqi: r.tqi,
              eta_seconds: r.eta_seconds,
              eta_p10: r.eta_p10,
              eta_p90: r.eta_p90,
              maneuver_detected: r.maneuver_detected,
              burst_score: r.burst_score,
              formation_id: r.formation_id,
              cross_oblast_score: r.cross_oblast_score,
              negative_evidence_score: r.negative_evidence_score,
              swarm_centroid: r.swarm_centroid,
              origin_inference: r.origin_inference,
              altitude_mode: r.altitude_mode,
              tracker_trail: r.tracker_trail,
              tracker_target: r.tracker_target,
            })),
          };

          const changed = ver !== lastVersion;
          lastVersion = ver;

          const event = changed
            ? `event: update\ndata: ${JSON.stringify(payload)}\n\n`
            : `event: heartbeat\ndata: ${JSON.stringify({ ts: nowMs, version: ver })}\n\n`;

          controller.enqueue(encoder.encode(event));
        } catch (err) {
          console.warn('[TRACKS_STREAM] push error:', err);
        }

        if (!closed && Date.now() < deadline) {
          setTimeout(push, PUSH_INTERVAL_MS);
        } else {
          try { controller.close(); } catch { /* already closed */ }
        }
      };

      // Initial push
      await push();
    },
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      Connection: 'keep-alive',
      'X-Accel-Buffering': 'no',
    },
  });
}
