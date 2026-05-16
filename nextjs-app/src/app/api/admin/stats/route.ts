import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { loadHidden, loadSettings } from '@/lib/admin/data';
import { buildMarkers, buildMarkerOptionsForApi } from '@/lib/build-markers';
import { initTargetStore, syncTargetStoreFromRedis, getTrackedTargetRecords } from '@/lib/tracked-target-store';

export const dynamic = 'force-dynamic';

export async function GET() {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  try {
    await initTargetStore();
    await syncTargetStoreFromRedis();
    const messages = getTrackedTargetRecords();
    const hidden = loadHidden();
    const settings = loadSettings();

    const markersWithGeo = messages.filter(m => m.lat && m.lng);
    const pendingGeo = messages.filter(m => m.pending_geo || (!m.lat && !m.lng));

    const publicMarkers = buildMarkers(buildMarkerOptionsForApi(true));
    const displayClassCounts: Record<string, number> = {};
    for (const m of publicMarkers) {
      const k = m.display_class ?? 'unknown';
      displayClassCounts[k] = (displayClassCounts[k] || 0) + 1;
    }

    return NextResponse.json({
      totalMessages: messages.length,
      markersCount: markersWithGeo.length,
      hiddenCount: hidden.length,
      pendingGeoCount: pendingGeo.length,
      displayClassCounts,
      settings: {
        monitorPeriod: settings.monitorPeriod,
        ttlEnabled: settings.ttlEnabled,
        minConfidence: settings.minConfidence,
        minConfidenceUav: settings.minConfidenceUav,
        spatialCorrelatorEnabled: settings.spatialCorrelatorEnabled ?? true,
      },
    });
  } catch (err) {
    console.error('[ADMIN STATS]', err);
    return NextResponse.json({ error: 'Failed to load stats' }, { status: 500 });
  }
}
