import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { loadMessages, loadHidden, loadBlocked, loadSettings } from '@/lib/admin/data';

export const dynamic = 'force-dynamic';

export async function GET() {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  try {
    const messages = loadMessages();
    const hidden = loadHidden();
    const blocked = loadBlocked();
    const settings = loadSettings();

    const markersWithGeo = messages.filter(m => m.lat && m.lng);
    const pendingGeo = messages.filter(m => m.pending_geo);

    return NextResponse.json({
      totalMessages: messages.length,
      markersCount: markersWithGeo.length,
      hiddenCount: hidden.length,
      blockedCount: blocked.length,
      pendingGeoCount: pendingGeo.length,
      settings: {
        monitorPeriod: settings.monitorPeriod,
        ttlEnabled: settings.ttlEnabled,
      },
    });
  } catch (err) {
    console.error('[ADMIN STATS]', err);
    return NextResponse.json({ error: 'Failed to load stats' }, { status: 500 });
  }
}
