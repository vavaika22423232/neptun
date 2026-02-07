import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { loadMessages } from '@/lib/admin/data';

export const dynamic = 'force-dynamic';

export async function GET() {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  try {
    const messages = loadMessages();
    // Filter pending geo messages (no lat/lng or pending_geo flag)
    const rawMsgs = messages
      .filter(m => m.pending_geo || (!m.lat && !m.lng))
      .sort((a, b) => {
        const da = new Date(a.date || a.timestamp || 0).getTime();
        const db = new Date(b.date || b.timestamp || 0).getTime();
        return db - da;
      })
      .slice(0, 100)
      .map(m => ({
        id: m.id || '',
        text: m.text || m.raw_text || '',
        date: m.date || m.timestamp || '',
        channel: m.channel || m.source || '',
        source: m.source || '',
        pending_geo: true,
      }));

    return NextResponse.json({ raw_msgs: rawMsgs });
  } catch (err) {
    console.error('[ADMIN RAW MSGS]', err);
    return NextResponse.json({ error: 'Failed to load raw messages' }, { status: 500 });
  }
}
