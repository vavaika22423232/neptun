import { cache, withETag } from '@/lib/cache';
import { getRawMessages } from '@/lib/markers-store';
import type { FusionTrajectory, FusionResponse } from '@/types';

const CACHE_KEY = 'fusion_trajectories';
const CACHE_TTL = 10_000; // 10 seconds
const STALE_TTL = 120_000; // 2 minutes

/**
 * Build fusion trajectories from in-memory markers store.
 * Zero file I/O — reads from the same singleton as /api/data.
 */
function buildFusionTrajectories(): FusionTrajectory[] {
  const messages = getRawMessages();
  const trajectories: FusionTrajectory[] = [];

  for (const m of messages) {
    if (m.fusion_trajectory) {
      const ft = m.fusion_trajectory as Record<string, unknown>;
      if (ft.actual_path && Array.isArray(ft.actual_path) && (ft.actual_path as unknown[]).length >= 2) {
        trajectories.push({
          event_id: (ft.event_id || m.id || '') as string,
          threat_type: (m.threat_type || 'drone') as string,
          actual_path: ft.actual_path as [number, number][],
          predicted_path: (ft.predicted_path || []) as [number, number][],
          confidence: (ft.confidence || 0) as number,
          last_seen: (m.date || '') as string,
        });
      }
    }
  }

  return trajectories;
}

export async function GET(request: Request) {
  const clientETag = request.headers.get('If-None-Match');

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
