/**
 * P5-A: GET /api/admin/tracks/predict
 *
 * Predictive alarm engine endpoint.  Returns a list of tracked targets that are
 * expected to cross user-defined regions of interest within `horizon_sec` seconds.
 *
 * Query params:
 *   horizon_sec   — look-ahead window in seconds (default: 300 = 5 min)
 *   regions       — JSON-encoded array of { id, lat, lng, radius_km } objects
 *
 * Example:
 *   GET /api/admin/tracks/predict?horizon_sec=600&regions=[{"id":"kyiv","lat":50.45,"lng":30.52,"radius_km":50}]
 *
 * Response:
 *   {
 *     generated_at: string,
 *     horizon_sec: number,
 *     alarms: [{ targetId, regionId, etaSec, confidence, target_details }]
 *   }
 */
import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';

export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  const url = new URL(request.url);
  const horizonSec = parseInt(url.searchParams.get('horizon_sec') ?? '300', 10) || 300;
  const regionsParam = url.searchParams.get('regions');

  type Region = { id: string; lat: number; lng: number; radiusKm: number };
  let regions: Region[] = [];

  if (regionsParam) {
    try {
      const parsed = JSON.parse(regionsParam);
      if (Array.isArray(parsed)) {
        regions = parsed
          .filter(
            (r) =>
              typeof r.id === 'string' &&
              typeof r.lat === 'number' &&
              typeof r.lng === 'number' &&
              (typeof r.radius_km === 'number' || typeof r.radiusKm === 'number'),
          )
          .map((r) => ({
            id: r.id as string,
            lat: r.lat as number,
            lng: r.lng as number,
            radiusKm: (r.radius_km ?? r.radiusKm) as number,
          }));
      }
    } catch {
      return NextResponse.json({ error: 'Invalid regions JSON' }, { status: 400 });
    }
  }

  // Default: major Ukrainian cities
  if (regions.length === 0) {
    regions = [
      { id: 'kyiv', lat: 50.45, lng: 30.52, radiusKm: 60 },
      { id: 'kharkiv', lat: 49.99, lng: 36.23, radiusKm: 40 },
      { id: 'dnipro', lat: 48.46, lng: 35.04, radiusKm: 40 },
      { id: 'odesa', lat: 46.47, lng: 30.73, radiusKm: 40 },
      { id: 'zaporizhzhia', lat: 47.84, lng: 35.14, radiusKm: 35 },
      { id: 'mykolaiv', lat: 46.97, lng: 32.0, radiusKm: 35 },
    ];
  }

  const { initTargetStore, syncTargetStoreFromRedis, getTrackerPredictiveAlarms, getTrackedTargetRecords } =
    await import('@/lib/tracked-target-store');

  await initTargetStore();
  await syncTargetStoreFromRedis();

  const alarms = getTrackerPredictiveAlarms(regions, horizonSec);
  const records = getTrackedTargetRecords();
  const recordMap = new Map(records.map((r) => [r.id as string, r]));

  const enrichedAlarms = alarms.map((alarm) => {
    const t = recordMap.get(alarm.targetId);
    return {
      ...alarm,
      confidence: Math.round(alarm.confidence * 100) / 100,
      target_details: t ? {
        threat_type: t.threat_type,
        lat: t.lat,
        lng: t.lng,
        speed_kmh: t.speed_kmh,
        course_bearing: t.course_bearing,
        tqi: t.tqi,
        formation_id: t.formation_id,
      } : null,
    };
  });

  return NextResponse.json({
    generated_at: new Date().toISOString(),
    horizon_sec: horizonSec,
    region_count: regions.length,
    alarms: enrichedAlarms,
    alarm_count: enrichedAlarms.length,
  });
}
