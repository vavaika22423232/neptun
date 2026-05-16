// Keep in sync with Next.js: `nextjs-app/src/lib/threat-bearing.ts`
// (MIN_TRACK_SEGMENT_KM, cardinal directions, resolve order).
import 'dart:math' as math;

import '../models/map_models.dart';

const double _minTrackSegmentKm = 0.45;
const double _deg = math.pi / 180;

const Map<String, double> _cardinalUk = {
  'захід': 270,
  'заходу': 270,
  'західного': 270,
  'західн': 270,
  'північ': 0,
  'півночі': 0,
  'північного': 0,
  'північн': 0,
  'схід': 90,
  'сходу': 90,
  'східного': 90,
  'східн': 90,
  'південь': 180,
  'півдня': 180,
  'південного': 180,
  'південн': 180,
  'північний захід': 315,
  'північного заходу': 315,
  'північний схід': 45,
  'північного сходу': 45,
  'південний захід': 225,
  'південного заходу': 225,
  'південний схід': 135,
  'південного сходу': 135,
};

double haversineKm(double lat1, double lng1, double lat2, double lng2) {
  const r = 6371.0;
  final dLat = (lat2 - lat1) * _deg;
  final dLng = (lng2 - lng1) * _deg;
  final a = math.sin(dLat / 2) * math.sin(dLat / 2) +
      math.cos(lat1 * _deg) *
          math.cos(lat2 * _deg) *
          math.sin(dLng / 2) *
          math.sin(dLng / 2);
  final c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a));
  return r * c;
}

/// Початковий азимут від (lat1,lng1) до (lat2,lng2), градуси 0–360 (0 = північ, за годинниковою).
double initialBearingDeg(
  double lat1,
  double lng1,
  double lat2,
  double lng2,
) {
  final phi1 = lat1 * _deg;
  final phi2 = lat2 * _deg;
  final dLambda = (lng2 - lng1) * _deg;
  final y = math.sin(dLambda) * math.cos(phi2);
  final x = math.cos(phi1) * math.sin(phi2) -
      math.sin(phi1) * math.cos(phi2) * math.cos(dLambda);
  var theta = math.atan2(y, x) * 180 / math.pi;
  theta = (theta + 360) % 360;
  return theta;
}

double? _normalizeBearing(double? v) {
  if (v == null || !v.isFinite) return null;
  return ((v % 360) + 360) % 360;
}

double? _bearingFromCardinalText(String? raw) {
  if (raw == null || raw.isEmpty) return null;
  final key = raw.toLowerCase().trim();
  if (_cardinalUk.containsKey(key)) return _cardinalUk[key];
  for (final e in _cardinalUk.entries) {
    if (key.contains(e.key)) return e.value;
  }
  return null;
}

double? _bearingFromProjectedPath(ThreatMarker marker) {
  final path = marker.projectedPath;
  if (path == null || path.length < 2) return null;
  for (var i = path.length - 1; i > 0; i--) {
    final a = path[i - 1];
    final b = path[i];
    final d = haversineKm(a.lat, a.lng, b.lat, b.lng);
    if (d >= _minTrackSegmentKm) {
      return initialBearingDeg(a.lat, a.lng, b.lat, b.lng);
    }
  }
  return null;
}

double? _bearingFromAiTrajectory(ThreatMarker marker) {
  final traj = marker.trajectory;
  if (traj == null || !traj.isValid) return null;
  final curLat = marker.lat;
  final curLng = marker.lng;
  final toEnd = haversineKm(curLat, curLng, traj.endLat, traj.endLng);
  if (toEnd >= _minTrackSegmentKm) {
    return initialBearingDeg(curLat, curLng, traj.endLat, traj.endLng);
  }
  final seg = haversineKm(traj.startLat, traj.startLng, traj.endLat, traj.endLng);
  if (seg >= _minTrackSegmentKm) {
    return initialBearingDeg(traj.startLat, traj.startLng, traj.endLat, traj.endLng);
  }
  return null;
}

/// Найкращий доступний кут руху загрози (градуси), узгоджено з `nextjs-app/src/lib/threat-bearing.ts`.
double? resolveThreatBearingDeg(ThreatMarker marker) {
  final fromPath = _bearingFromProjectedPath(marker);
  if (fromPath != null) return fromPath;

  final fromTraj = _bearingFromAiTrajectory(marker);
  if (fromTraj != null) return fromTraj;

  final cb = _normalizeBearing(marker.courseBearing);
  if (cb != null) return cb;

  final tb = _normalizeBearing(marker.tickerBearing);
  if (tb != null) return tb;

  final fromCourse = _bearingFromCardinalText(marker.courseDirection);
  if (fromCourse != null) return fromCourse;

  final fromArrow = _bearingFromCardinalText(marker.arrowDirection);
  if (fromArrow != null) return fromArrow;

  return null;
}

/// `Canvas.rotate`: той самий знак, що й веб `bearingToWebIconRotationCssDeg` (нос іконки вгору при 0°).
double canvasRotationRadMatchingWeb(double bearingDeg) {
  final b = ((bearingDeg % 360) + 360) % 360;
  return b * math.pi / 180;
}
