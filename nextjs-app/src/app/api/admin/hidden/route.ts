import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { loadHidden } from '@/lib/admin/data';

export const dynamic = 'force-dynamic';

export async function GET() {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  try {
    const hidden = loadHidden();
    // Parse hidden entries — stored as "lat,lng|text|source"
    const parsed = hidden.map(entry => {
      const parts = entry.split('|');
      const coords = (parts[0] || '').split(',');
      return {
        lat: coords[0] || '',
        lng: coords[1] || '',
        text: parts[1] || '',
        source: parts[2] || '',
        key: entry,
      };
    });

    return NextResponse.json({ hidden: parsed });
  } catch (err) {
    console.error('[ADMIN HIDDEN]', err);
    return NextResponse.json({ error: 'Failed to load hidden' }, { status: 500 });
  }
}
