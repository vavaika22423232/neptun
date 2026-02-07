import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { loadSettings, saveSettings } from '@/lib/admin/data';

export const dynamic = 'force-dynamic';

export async function GET() {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  try {
    const settings = loadSettings();
    return NextResponse.json({ enabled: settings.ttlEnabled });
  } catch (err) {
    console.error('[ADMIN TTL GET]', err);
    return NextResponse.json({ error: 'Failed' }, { status: 500 });
  }
}

export async function POST(request: Request) {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  try {
    const body = await request.json();
    const enabled = Boolean(body.enabled);

    const settings = loadSettings();
    settings.ttlEnabled = enabled;
    saveSettings(settings);

    return NextResponse.json({ status: 'ok', enabled });
  } catch (err) {
    console.error('[ADMIN TTL POST]', err);
    return NextResponse.json({ error: 'Failed' }, { status: 500 });
  }
}
