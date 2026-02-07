import { NextResponse } from 'next/server';
import { cache, withETag } from '@/lib/cache';
import fs from 'fs';
import path from 'path';
import type { FusionTrajectory, FusionResponse } from '@/types';

const CACHE_KEY = 'fusion_trajectories';
const CACHE_TTL = 10_000; // 10 seconds
const STALE_TTL = 120_000; // 2 minutes

const DATA_DIR = process.env.DATA_DIR || '/data';
const MESSAGES_FILE = path.join(DATA_DIR, 'messages.json');
const FALLBACK_MESSAGES_FILE = path.resolve(process.cwd(), '..', 'messages.json');

/**
 * Build fusion trajectories from messages that have multi-point paths.
 * This is a simplified version - the Python worker does the heavy lifting.
 */
function buildFusionTrajectories(): FusionTrajectory[] {
  const filePaths = [MESSAGES_FILE, FALLBACK_MESSAGES_FILE];

  for (const filePath of filePaths) {
    try {
      if (fs.existsSync(filePath)) {
        const raw = fs.readFileSync(filePath, 'utf-8');
        const data = JSON.parse(raw);
        const messages = Array.isArray(data) ? data : data.messages || [];

        // Extract messages with trajectory paths
        const trajectories: FusionTrajectory[] = [];

        messages.forEach((m: Record<string, unknown>) => {
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
        });

        return trajectories;
      }
    } catch (err) {
      console.warn(`[FUSION] Failed to read ${filePath}:`, err);
    }
  }

  return [];
}

export async function GET(request: Request) {
  const clientETag = request.headers.get('If-None-Match');

  // Check cache
  const { entry, isStale } = cache.getWithStale<FusionResponse>(CACHE_KEY, STALE_TTL);

  if (entry && !isStale) {
    return withETag(entry.data, entry.etag, clientETag);
  }

  // Build fresh data
  const trajectories = buildFusionTrajectories();
  const responseData: FusionResponse = {
    status: 'ok',
    trajectories,
    count: trajectories.length,
  };

  const newEntry = cache.set(CACHE_KEY, responseData, CACHE_TTL);
  return withETag(newEntry.data, newEntry.etag, clientETag);
}
