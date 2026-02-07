import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { loadSettings, saveSettings } from '@/lib/admin/data';

export const dynamic = 'force-dynamic';

export async function GET() {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  try {
    const settings = loadSettings();
    return NextResponse.json({ value: settings.monitorPeriod });
  } catch (err) {
    console.error('[ADMIN MONITOR PERIOD GET]', err);
    return NextResponse.json({ error: 'Failed' }, { status: 500 });
  }
}

export async function POST(request: Request) {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  try {
    const body = await request.json();
    const value = Number(body.value);
    if (isNaN(value) || value < 1 || value > 360) {
      return NextResponse.json({ error: 'Value must be 1-360' }, { status: 400 });
    }

    const settings = loadSettings();
    settings.monitorPeriod = value;
    saveSettings(settings);

    return NextResponse.json({ status: 'ok', value });
  } catch (err) {
    console.error('[ADMIN MONITOR PERIOD POST]', err);
    return NextResponse.json({ error: 'Failed' }, { status: 500 });
  }
}
