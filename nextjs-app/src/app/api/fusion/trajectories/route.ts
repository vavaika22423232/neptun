import { cache, withETag } from '@/lib/cache';
import { getTrackedTargetRecords, initTargetStore } from '@/lib/tracked-target-store';
import type { FusionTrajectory, FusionResponse } from '@/types';

const CACHE_KEY = 'fusion_trajectories';
const CACHE_TTL = 10_000; // 10 seconds
const STALE_TTL = 120_000; // 2 minutes

/**
 * Build fusion trajectories from in-memory track store.
 */
function buildFusionTrajectories(): FusionTrajectory[] {
  const messages = getTrackedTargetRecords();
  const trajectories: FusionTrajectory[] = [];

  for (const m of messages) {
    if (m.positions && Array.isArray(m.positions) && (m.positions as unknown[]).length >= 2) {
      trajectories.push({
        event_id: (m.track_id || m.id || '') as string,
        threat_type: (m.threat_type || 'drone') as string,
        actual_path: m.positions.map((p: any) => [p.lat, p.lng] as [number, number]),
        predicted_path: [],
        confidence: (m.track_confidence || 0) as number,
        last_seen: (m.date || '') as string,
      });
    }
  }

  return trajectories;
}

export async function GET(request: Request) {
  const clientETag = request.headers.get('If-None-Match');
  await initTargetStore();

  const { entry, isStale } = cache.getWithStale<FusionResponse>(CACHE_KEY, STALE_TTL);

  if (entry && !isStale) {
    return withETag(entry.data, entry.etag, clientETag, undefined, entry.json);
  }

  const trajectories = buildFusionTrajectories();
  const responseData: FusionResponse = {
    status: 'ok',
    trajectories,
    count: trajectories.length,
  };

  const newEntry = cache.set(CACHE_KEY, responseData, CACHE_TTL);
  return withETag(newEntry.data, newEntry.etag, clientETag, undefined, newEntry.json);
}
