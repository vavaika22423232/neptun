import { NextResponse } from 'next/server';
import { cache } from '@/lib/cache';
import type { Alarm } from '@/types';

const CACHE_KEY = 'alarms_all';
const STALE_TTL = 7200_000;

/**
 * GET /api/alarm-status
 * Returns alarm status per region for the mobile app's alarm timer widget.
 */
export async function GET() {
  const { entry } = cache.getWithStale<Alarm[]>(CACHE_KEY, STALE_TTL);

  const alerts: Record<string, { active: boolean; start_time: string | null; type: string | null }> = {};

  if (entry?.data) {
    for (const region of entry.data) {
      if (region.activeAlerts && region.activeAlerts.length > 0) {
        const alert = region.activeAlerts[0];
        alerts[region.regionName || region.regionId] = {
          active: true,
          start_time: alert.lastUpdate || null,
          type: alert.type || 'Повітряна тривога',
        };
      }
    }
  }

  return NextResponse.json({ alerts });
}
