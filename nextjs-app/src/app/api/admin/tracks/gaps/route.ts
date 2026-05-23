import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';

export const dynamic = 'force-dynamic';

function toMs(value: unknown): number {
  const n = typeof value === 'number' ? value : Number(value);
  if (!Number.isFinite(n) || n <= 0) return 0;
  return n > 10_000_000_000 ? n : n * 1000;
}

function label(value: unknown, fallback = 'unknown'): string {
  const s = String(value || '').trim();
  return s || fallback;
}

function inc(bucket: Record<string, number>, key: unknown): void {
  const k = label(key);
  bucket[k] = (bucket[k] || 0) + 1;
}

function incMatrix(bucket: Record<string, Record<string, number>>, row: unknown, col: unknown): void {
  const r = label(row);
  const c = label(col);
  if (!bucket[r]) bucket[r] = {};
  bucket[r][c] = (bucket[r][c] || 0) + 1;
}

export async function GET(request: Request) {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  const url = new URL(request.url);
  const limit = Math.max(1, Math.min(200, Number(url.searchParams.get('limit') || 80)));
  const minutes = Math.max(1, Math.min(240, Number(url.searchParams.get('minutes') || 30)));
  const type = url.searchParams.get('type')?.trim().toLowerCase();
  const reasonFilter = url.searchParams.get('reason')?.trim().toLowerCase();
  const freshCutoffMs = Date.now() - minutes * 60 * 1000;

  const {
    getTrackedTargetRecords,
    initTargetStore,
    syncTargetStoreFromRedis,
  } = await import('@/lib/tracked-target-store');
  const { loadHidden, loadSettings } = await import('@/lib/admin/data');
  const {
    explainPublicMapRawFilter,
    parseRawMarkerMessageTimeMs,
  } = await import('@/lib/marker-publication');
  const { evaluateMarkerPublication } = await import('@/lib/public-marker-policy');

  await initTargetStore();
  await syncTargetStoreFromRedis();

  const settings = loadSettings();
  const hiddenSet = new Set(loadHidden());
  const ttlCutoffMs = settings.ttlEnabled !== false
    ? Date.now() - (settings.monitorPeriod || 30) * 60 * 1000
    : 0;

  const gaps = [];
  const summary: Record<string, number> = {};
  const summaryByRegion: Record<string, number> = {};
  const summaryByType: Record<string, number> = {};
  const summaryByRadarState: Record<string, number> = {};
  const summaryByEvidenceLevel: Record<string, number> = {};
  const summaryByObservationQuality: Record<string, number> = {};
  const summaryByTextIntent: Record<string, number> = {};
  const reasonByRegion: Record<string, Record<string, number>> = {};
  const reasonByObservationQuality: Record<string, Record<string, number>> = {};

  for (const track of getTrackedTargetRecords()) {
    if (type && String(track.threat_type || track.type || '').toLowerCase() !== type) continue;

    const messageTimeMs = parseRawMarkerMessageTimeMs(track);
    const activityMs = Math.max(
      messageTimeMs > 0 ? messageTimeMs : 0,
      toMs(track.last_update_epoch),
      toMs(track.created_at_epoch),
    );
    if (activityMs > 0 && activityMs < freshCutoffMs) continue;

    const publicMap = explainPublicMapRawFilter(track, {
      settings,
      ttlEnabled: settings.ttlEnabled !== false,
      cutoffMs: ttlCutoffMs,
      hiddenSet,
      messageTimeMs,
    });
    if (publicMap.passes) continue;
    if (reasonFilter && publicMap.reason !== reasonFilter) continue;

    summary[publicMap.reason] = (summary[publicMap.reason] || 0) + 1;
    inc(summaryByRegion, track.region);
    inc(summaryByType, track.threat_type || track.type);
    inc(summaryByRadarState, track.radar_state || track.track_state);
    inc(summaryByEvidenceLevel, track.evidence_level);
    inc(summaryByObservationQuality, track.last_observation_quality || track.position_source || track.resolve_status);
    inc(summaryByTextIntent, track.last_text_intent);
    incMatrix(reasonByRegion, track.region, publicMap.reason);
    incMatrix(reasonByObservationQuality, track.last_observation_quality || track.position_source || track.resolve_status, publicMap.reason);
    const publication = evaluateMarkerPublication(track, { settings, hidden: false });

    gaps.push({
      id: track.id,
      track_id: track.track_id,
      threat_type: track.threat_type || track.type,
      place: track.place || track.city || track.location,
      region: track.region,
      lifecycle: track.target_lifecycle_state,
      track_state: track.track_state,
      confidence: track.confidence,
      target_confidence: track.target_confidence,
      track_confidence: track.track_confidence,
      radar_state: track.radar_state,
      uncertainty_radius_km: track.uncertainty_radius_km,
      evidence_level: track.evidence_level,
      observation_quality: track.last_observation_quality,
      text_intent: track.last_text_intent,
      source_count: track.source_count,
      count: track.count,
      current: { lat: track.lat, lng: track.lng, ts: track.last_update_epoch },
      observed: track.last_observation ?? null,
      predicted: track.predicted_position ?? null,
      measurement: track.last_measurement ?? null,
      association: track.last_association ?? null,
      publication: {
        class: publication.classification,
        score: publication.score,
        reasons: publication.reasons,
        invariant_violations: publication.invariantViolations,
      },
      gap: {
        reason: publicMap.reason,
        details: publicMap.details ?? {},
        message_time_ms: messageTimeMs,
        activity_ms: activityMs,
        age_ms: activityMs > 0 ? Date.now() - activityMs : null,
        ttl_cutoff_ms: ttlCutoffMs,
      },
    });
  }

  gaps.sort((a, b) => Number(b.gap.activity_ms || 0) - Number(a.gap.activity_ms || 0));

  return NextResponse.json({
    status: 'ok',
    minutes,
    limit,
    count: Math.min(gaps.length, limit),
    total_matching: gaps.length,
    summary,
    summary_by_region: summaryByRegion,
    summary_by_type: summaryByType,
    summary_by_radar_state: summaryByRadarState,
    summary_by_evidence_level: summaryByEvidenceLevel,
    summary_by_observation_quality: summaryByObservationQuality,
    summary_by_text_intent: summaryByTextIntent,
    reason_by_region: reasonByRegion,
    reason_by_observation_quality: reasonByObservationQuality,
    gaps: gaps.slice(0, limit),
  });
}
