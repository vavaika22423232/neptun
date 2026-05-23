/** Pure parsing helpers — Flutter `RadarRepository` parity (testable without RN). */

export function parseThreatsEnvelope(decoded: unknown): Record<string, unknown>[] {
  if (Array.isArray(decoded)) {
    return decoded.filter((x) => x != null && typeof x === 'object') as Record<string, unknown>[];
  }
  if (decoded != null && typeof decoded === 'object') {
    const map = decoded as Record<string, unknown>;
    if (Array.isArray(map.threats)) {
      return map.threats as Record<string, unknown>[];
    }
    if (Array.isArray(map.markers)) {
      return map.markers as Record<string, unknown>[];
    }
  }
  return [];
}

export function normalizeThreatMarker(raw: Record<string, unknown>): Record<string, unknown> {
  const m = { ...raw };
  const pi = m.predicted_impact ?? m.predictedImpact;
  if (pi != null && typeof pi === 'object' && !Array.isArray(pi)) {
    m.predicted_impact = pi as Record<string, unknown>;
  }
  m.track_quality_score ??= m.trackQualityScore ?? m.quality_score ?? m.qualityScore;
  m.formation_id ??= m.formationId ?? m.wave_id ?? m.waveId;
  if (m.maneuver_detected == null) {
    m.maneuver_detected = m.maneuverDetected === true;
  }
  m.impact_zone_km ??= m.impactZoneKm;
  return m;
}

export function countActiveRegionsFromAlarmStream(rows: unknown[]): number {
  let count = 0;
  for (const r of rows) {
    if (r != null && typeof r === 'object') {
      const alerts = (r as Record<string, unknown>).activeAlerts;
      if (Array.isArray(alerts) && alerts.length > 0) count += 1;
    }
  }
  return count;
}
