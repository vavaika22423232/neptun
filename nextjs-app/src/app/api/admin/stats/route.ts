import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { loadMessages, loadHidden, loadBlocked, loadSettings } from '@/lib/admin/data';
import { buildMarkers, buildMarkerOptionsForApi } from '@/lib/build-markers';
import { initStore } from '@/lib/markers-store';

export const dynamic = 'force-dynamic';

export async function GET() {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  try {
    await initStore();
    const messages = loadMessages();
    const hidden = loadHidden();
    const blocked = loadBlocked();
    const settings = loadSettings();

    const markersWithGeo = messages.filter(m => m.lat && m.lng);
    const pendingGeo = messages.filter(m => m.pending_geo);

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
      blockedCount: blocked.length,
      pendingGeoCount: pendingGeo.length,
      displayClassCounts,
      settings: {
        monitorPeriod: settings.monitorPeriod,
        ttlEnabled: settings.ttlEnabled,
        minConfidence: settings.minConfidence,
        spatialCorrelatorEnabled: settings.spatialCorrelatorEnabled ?? true,
        dualSourceMapGate: settings.dualSourceMapGate ?? true,
        corroborationMinObservations: settings.corroborationMinObservations ?? 2,
        corroborationWindowMinutes: settings.corroborationWindowMinutes ?? 30,
        corroborationMaxRadiusKm: settings.corroborationMaxRadiusKm ?? 45,
        corroborationMinDistinctSources: settings.corroborationMinDistinctSources ?? 0,
        regionUncertaintyKm: settings.regionUncertaintyKm ?? 38,
        corroboratedUncertaintyKm: settings.corroboratedUncertaintyKm ?? 9,
      },
    });
  } catch (err) {
    console.error('[ADMIN STATS]', err);
    return NextResponse.json({ error: 'Failed to load stats' }, { status: 500 });
  }
}
