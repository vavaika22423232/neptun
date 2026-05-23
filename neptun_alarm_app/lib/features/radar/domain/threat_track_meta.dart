/// V10+ поля треку з `/api/threats` для UI бейджів.
class ThreatTrackMeta {
  const ThreatTrackMeta({
    this.trackQualityScore,
    this.predictedImpact,
    this.formationId,
    this.maneuverDetected = false,
    this.impactZoneKm,
  });

  final double? trackQualityScore;
  final Map<String, dynamic>? predictedImpact;
  final String? formationId;
  final bool maneuverDetected;
  final double? impactZoneKm;

  factory ThreatTrackMeta.fromMarker(Map<String, dynamic> m) {
    final pi = m['predicted_impact'] ?? m['predictedImpact'];
    Map<String, dynamic>? impact;
    if (pi is Map) {
      impact = Map<String, dynamic>.from(pi);
    }

    return ThreatTrackMeta(
      trackQualityScore: _readDouble(
        m['track_quality_score'] ?? m['trackQualityScore'],
      ),
      predictedImpact: impact,
      formationId: (m['formation_id'] ?? m['formationId'])?.toString(),
      maneuverDetected:
          m['maneuver_detected'] == true || m['maneuverDetected'] == true,
      impactZoneKm: _readDouble(m['impact_zone_km'] ?? m['impactZoneKm']),
    );
  }

  /// «~N хв» до прогнозованого удару.
  String? get predictedEtaLabel {
    final pi = predictedImpact;
    if (pi == null) return null;
    final raw = pi['eta_minutes'] ?? pi['etaMinutes'] ?? pi['minutes'];
    final minutes = _readDouble(raw);
    if (minutes == null || minutes <= 0) return null;
    return '~${minutes.round()} хв';
  }

  int? get qualityPercent {
    final q = trackQualityScore;
    if (q == null) return null;
    if (q <= 1) return (q * 100).round().clamp(0, 100);
    return q.round().clamp(0, 100);
  }

  bool get hasWaveBadge =>
      formationId != null && formationId!.trim().isNotEmpty;

  static double? _readDouble(Object? raw) {
    if (raw == null) return null;
    if (raw is num) return raw.toDouble();
    return double.tryParse(raw.toString());
  }
}
