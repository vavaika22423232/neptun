import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { loadSettings, saveSettings, type AdminSettings } from '@/lib/admin/data';

export const dynamic = 'force-dynamic';

function clamp(n: number, lo: number, hi: number): number {
  return Math.min(hi, Math.max(lo, n));
}

export async function POST(request: Request) {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  try {
    const body = (await request.json()) as Record<string, unknown>;
    const settings = loadSettings();

    if (typeof body.spatialCorrelatorEnabled === 'boolean') {
      settings.spatialCorrelatorEnabled = body.spatialCorrelatorEnabled;
    }
    if (body.minConfidenceUav === null) {
      delete settings.minConfidenceUav;
    } else if (body.minConfidenceUav !== undefined) {
      const v = Number(body.minConfidenceUav);
      if (!Number.isFinite(v)) {
        return NextResponse.json({ error: 'minConfidenceUav invalid' }, { status: 400 });
      }
      settings.minConfidenceUav = clamp(v, 0.1, 1);
    }

    saveSettings(settings);

    return NextResponse.json({
      ok: true,
      spatialCorrelatorEnabled: settings.spatialCorrelatorEnabled,
      minConfidenceUav: settings.minConfidenceUav,
    });
  } catch (err) {
    console.error('[ADMIN TRUST DISPLAY]', err);
    return NextResponse.json({ error: 'Failed' }, { status: 500 });
  }
}
