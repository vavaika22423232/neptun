import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { loadHidden, saveHidden } from '@/lib/admin/data';

export async function POST(request: Request) {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  try {
    const body = await request.json();
    const { lat, lng, text, source } = body;

    const key = `${lat},${lng}|${text || ''}|${source || ''}`;
    const hidden = loadHidden();
    if (!hidden.includes(key)) {
      hidden.push(key);
      saveHidden(hidden);
    }

    return NextResponse.json({ status: 'ok', key });
  } catch (err) {
    console.error('[ADMIN HIDE]', err);
    return NextResponse.json({ error: 'Failed to hide marker' }, { status: 500 });
  }
}
