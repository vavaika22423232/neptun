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
    if (typeof body.dualSourceMapGate === 'boolean') {
      settings.dualSourceMapGate = body.dualSourceMapGate;
    }
    if (body.corroborationMinObservations != null) {
      const v = Number(body.corroborationMinObservations);
      if (!Number.isFinite(v)) {
        return NextResponse.json({ error: 'corroborationMinObservations invalid' }, { status: 400 });
      }
      settings.corroborationMinObservations = clamp(Math.round(v), 1, 20);
    }
    if (body.corroborationWindowMinutes != null) {
      const v = Number(body.corroborationWindowMinutes);
      if (!Number.isFinite(v)) {
        return NextResponse.json({ error: 'corroborationWindowMinutes invalid' }, { status: 400 });
      }
      settings.corroborationWindowMinutes = clamp(Math.round(v), 1, 180);
    }
    if (body.corroborationMaxRadiusKm != null) {
      const v = Number(body.corroborationMaxRadiusKm);
      if (!Number.isFinite(v)) {
        return NextResponse.json({ error: 'corroborationMaxRadiusKm invalid' }, { status: 400 });
      }
      settings.corroborationMaxRadiusKm = clamp(v, 1, 200);
    }
    if (body.corroborationMinDistinctSources != null) {
      const v = Number(body.corroborationMinDistinctSources);
      if (!Number.isFinite(v)) {
        return NextResponse.json({ error: 'corroborationMinDistinctSources invalid' }, { status: 400 });
      }
      settings.corroborationMinDistinctSources = clamp(Math.round(v), 0, 10);
    }
    if (body.regionUncertaintyKm != null) {
      const v = Number(body.regionUncertaintyKm);
      if (!Number.isFinite(v)) {
        return NextResponse.json({ error: 'regionUncertaintyKm invalid' }, { status: 400 });
      }
      settings.regionUncertaintyKm = clamp(v, 5, 150);
    }
    if (body.corroboratedUncertaintyKm != null) {
      const v = Number(body.corroboratedUncertaintyKm);
      if (!Number.isFinite(v)) {
        return NextResponse.json({ error: 'corroboratedUncertaintyKm invalid' }, { status: 400 });
      }
      settings.corroboratedUncertaintyKm = clamp(v, 1, 80);
    }

    saveSettings(settings);

    const out: Partial<AdminSettings> = {
      spatialCorrelatorEnabled: settings.spatialCorrelatorEnabled,
      dualSourceMapGate: settings.dualSourceMapGate,
      corroborationMinObservations: settings.corroborationMinObservations,
      corroborationWindowMinutes: settings.corroborationWindowMinutes,
      corroborationMaxRadiusKm: settings.corroborationMaxRadiusKm,
      corroborationMinDistinctSources: settings.corroborationMinDistinctSources,
      regionUncertaintyKm: settings.regionUncertaintyKm,
      corroboratedUncertaintyKm: settings.corroboratedUncertaintyKm,
    };

    return NextResponse.json({ ok: true, ...out });
  } catch (err) {
    console.error('[ADMIN TRUST DISPLAY]', err);
    return NextResponse.json({ error: 'Failed' }, { status: 500 });
  }
}
