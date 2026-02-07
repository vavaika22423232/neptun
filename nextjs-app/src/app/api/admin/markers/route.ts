import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { loadMessages } from '@/lib/admin/data';

export const dynamic = 'force-dynamic';

export async function GET() {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  try {
    const messages = loadMessages();
    // Show markers that have lat/lng, most recent first, up to 120
    const markers = messages
      .filter(m => m.lat && m.lng)
      .sort((a, b) => {
        const da = new Date(a.date || a.timestamp || 0).getTime();
        const db = new Date(b.date || b.timestamp || 0).getTime();
        return db - da;
      })
      .slice(0, 120)
      .map(m => ({
        id: m.id || `${m.lat}_${m.lng}_${m.date}`,
        lat: Number(m.lat),
        lng: Number(m.lng),
        threat_type: m.threat_type || m.type || 'default',
        place: m.place || m.city || '',
        text: m.text || '',
        date: m.date || m.timestamp || '',
        manual: m.manual || false,
        rotation: m.rotation || 0,
        count: m.count || 1,
        course_direction: m.course_direction || '',
      }));

    return NextResponse.json({ markers });
  } catch (err) {
    console.error('[ADMIN MARKERS]', err);
    return NextResponse.json({ error: 'Failed to load markers' }, { status: 500 });
  }
}
