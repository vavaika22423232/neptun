import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { initTargetStore, getTrackedTargetRecords } from '@/lib/tracked-target-store';

export const dynamic = 'force-dynamic';

/** Histogram of resolve_status and confidence buckets from current track store (Redis-backed). */
export async function GET() {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  try {
    await initTargetStore();
    const messages = getTrackedTargetRecords();
    const byStatus: Record<string, number> = {};
    const buckets = { b0: 0, b02: 0, b04: 0, b06: 0, b08: 0, na: 0 };
    let sumConf = 0;
    let nConf = 0;

    for (const m of messages) {
      const rs = String((m as Record<string, unknown>).resolve_status || '').trim() || '(empty)';
      byStatus[rs] = (byStatus[rs] || 0) + 1;

      const c = (m as Record<string, unknown>).confidence;
      if (typeof c === 'number' && Number.isFinite(c)) {
        sumConf += c;
        nConf += 1;
        if (c < 0.2) buckets.b0 += 1;
        else if (c < 0.4) buckets.b02 += 1;
        else if (c < 0.6) buckets.b04 += 1;
        else if (c < 0.8) buckets.b06 += 1;
        else buckets.b08 += 1;
      } else {
        buckets.na += 1;
      }
    }

    return NextResponse.json({
      sampleSize: messages.length,
      byResolveStatus: byStatus,
      confidenceBuckets: {
        '0.0–0.2': buckets.b0,
        '0.2–0.4': buckets.b02,
        '0.4–0.6': buckets.b04,
        '0.6–0.8': buckets.b06,
        '0.8–1.0': buckets.b08,
        missing: buckets.na,
      },
      meanConfidence: nConf > 0 ? Math.round((sumConf / nConf) * 1000) / 1000 : null,
    });
  } catch (err) {
    console.error('[ADMIN RESOLVE-QUALITY]', err);
    return NextResponse.json({ error: 'Failed to aggregate resolve quality' }, { status: 500 });
  }
}
