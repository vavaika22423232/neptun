import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';

export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  const url = new URL(request.url);
  const limit = Math.max(1, Math.min(200, Number(url.searchParams.get('limit') || 80)));
  const state = url.searchParams.get('state')?.trim().toLowerCase();
  const type = url.searchParams.get('type')?.trim().toLowerCase();

  const {
    getTrackedTargetRecords,
    initTargetStore,
    syncTargetStoreFromRedis,
  } = await import('@/lib/tracked-target-store');
  const { loadHidden, loadSettings } = await import('@/lib/admin/data');
  const {
    explainPublicMapRawFilter,
    parseRawMarkerMessageTimeMs,
  } = await import('@/lib/marker-publication');
  const { evaluateMarkerPublication } = await import('@/lib/public-marker-policy');

  await initTargetStore();
  await syncTargetStoreFromRedis();

  const settings = loadSettings();
  const hiddenSet = new Set(loadHidden());
  const cutoffMs = settings.ttlEnabled !== false
    ? Date.now() - (settings.monitorPeriod || 30) * 60 * 1000
    : 0;

  const tracks = getTrackedTargetRecords()
    .filter((track) => {
      if (state && String(track.track_state || '').toLowerCase() !== state) return false;
      if (type && String(track.threat_type || track.type || '').toLowerCase() !== type) return false;
      return true;
    })
    .sort((a, b) => Number(b.last_update_epoch || 0) - Number(a.last_update_epoch || 0))
    .slice(0, limit)
    .map((track) => {
      const messageTimeMs = parseRawMarkerMessageTimeMs(track);
      const publication = evaluateMarkerPublication(track, { settings, hidden: false });
      const publicMap = explainPublicMapRawFilter(track, {
        settings,
        ttlEnabled: settings.ttlEnabled !== false,
        cutoffMs,
        hiddenSet,
        messageTimeMs,
      });
      return {
        id: track.id,
        threat_type: track.threat_type,
        region: track.region,
        place: track.place,
        lifecycle: track.target_lifecycle_state,
        track_state: track.track_state,
        confidence: track.target_confidence,
        visual_confidence: track.track_confidence,
        source_count: track.source_count,
        count: track.count,
        current: { lat: track.lat, lng: track.lng, ts: track.last_update_epoch },
        observed: track.last_observation ?? null,
        predicted: track.predicted_position ?? null,
        measurement: track.last_measurement ?? null,
        association: track.last_association ?? null,
        motion_reason: track.motion_reason,
        heading_confidence: track.heading_confidence,
        position_estimated: track.position_estimated === true,
        is_loitering: track.is_loitering === true,
        eta_seconds: track.eta_seconds ?? null,
        accepted_observations: Array.isArray(track.observations) ? track.observations.length : 0,
        rejected_observations: Array.isArray(track.rejected_observations)
          ? track.rejected_observations.slice(-8)
          : [],
        upstream_track_ids: track.upstream_track_ids ?? [],
        publication: {
          class: publication.classification,
          score: publication.score,
          reasons: publication.reasons,
          invariant_violations: publication.invariantViolations,
        },
        public_map: {
          passes: publicMap.passes,
          reason: publicMap.reason,
          details: publicMap.details ?? {},
          message_time_ms: messageTimeMs,
          ttl_cutoff_ms: cutoffMs,
        },
      };
    });

  return NextResponse.json({
    status: 'ok',
    count: tracks.length,
    tracks,
  });
}
