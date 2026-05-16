import { NextResponse } from 'next/server';
import { redisGet } from '@/lib/redis';
import { alarmRegionNameAliases } from '@/lib/map/alarm-hasc-filter';
import type { Alarm } from '@/types';

const REDIS_KEY = 'alarms:all';
const REDIS_META_KEY = 'alarms:last_updated';

/**
 * GET /api/alarm-status
 * Returns alarm status per region for the mobile app's alarm timer widget.
 * Reads from Redis — shared between all contexts, survives restarts.
 */
export async function GET() {
  const [alarms, lastUpdated] = await Promise.all([
    redisGet<Alarm[]>(REDIS_KEY),
    redisGet<string>(REDIS_META_KEY),
  ]);

  const alerts: Record<string, { active: boolean; start_time: string | null; type: string | null }> = {};

  if (alarms && Array.isArray(alarms)) {
    for (const region of alarms) {
      if (region.activeAlerts && region.activeAlerts.length > 0) {
        const alert = region.activeAlerts[0];
        alerts[region.regionName || region.regionId] = {
          active: true,
          start_time: alert.lastUpdate || null,
          type: alert.type || 'Повітряна тривога',
        };
        for (const alias of alarmRegionNameAliases(region.regionName || '')) {
          if (!alias || alerts[alias]) continue;
          alerts[alias] = {
            active: true,
            start_time: alert.lastUpdate || null,
            type: alert.type || 'Повітряна тривога',
          };
        }
      }
    }
  }

  return NextResponse.json({
    alerts,
    last_updated: lastUpdated || null,
    data_age: lastUpdated ? Math.round((Date.now() - new Date(lastUpdated).getTime()) / 1000) : null,
  });
}
