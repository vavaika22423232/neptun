export type ThreatTrackMeta = {
  trackQualityScore?: number;
  predictedImpact?: Record<string, unknown>;
  formationId?: string;
  maneuverDetected: boolean;
  impactZoneKm?: number;
};

function readDouble(raw: unknown): number | undefined {
  if (raw == null) return undefined;
  if (typeof raw === 'number') return raw;
  const n = Number(raw);
  return Number.isFinite(n) ? n : undefined;
}

export function threatTrackMetaFromMarker(m: Record<string, unknown>): ThreatTrackMeta {
  const pi = m.predicted_impact ?? m.predictedImpact;
  let predictedImpact: Record<string, unknown> | undefined;
  if (pi != null && typeof pi === 'object' && !Array.isArray(pi)) {
    predictedImpact = pi as Record<string, unknown>;
  }
  return {
    trackQualityScore: readDouble(m.track_quality_score ?? m.trackQualityScore ?? m.quality_score),
    predictedImpact,
    formationId: String(m.formation_id ?? m.formationId ?? '').trim() || undefined,
    maneuverDetected: m.maneuver_detected === true || m.maneuverDetected === true,
    impactZoneKm: readDouble(m.impact_zone_km ?? m.impactZoneKm),
  };
}

export function predictedEtaLabel(meta: ThreatTrackMeta): string | undefined {
  const pi = meta.predictedImpact;
  if (!pi) return undefined;
  const minutes = readDouble(pi.eta_minutes ?? pi.etaMinutes ?? pi.minutes);
  if (minutes == null || minutes <= 0) return undefined;
  return `~${Math.round(minutes)} хв`;
}

export function qualityPercent(meta: ThreatTrackMeta): number | undefined {
  const q = meta.trackQualityScore;
  if (q == null) return undefined;
  if (q <= 1) return Math.min(100, Math.max(0, Math.round(q * 100)));
  return Math.min(100, Math.max(0, Math.round(q)));
}

export function hasWaveBadge(meta: ThreatTrackMeta): boolean {
  return !!meta.formationId?.trim();
}
