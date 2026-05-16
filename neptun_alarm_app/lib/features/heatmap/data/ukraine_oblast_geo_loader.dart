import 'dart:convert';
import 'dart:math' as math;
import 'dart:ui' show Color, StrokeCap, StrokeJoin;

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

/// GADM HASC_1 → числовий id області для теплової карти (`1`…`27`).
const Map<String, String> kHascToHeatmapStateId = {
  'UA.VI': '1',
  'UA.VO': '2',
  'UA.DP': '3',
  'UA.DT': '4',
  'UA.ZT': '5',
  'UA.ZK': '6',
  'UA.ZP': '7',
  'UA.IF': '8',
  'UA.KV': '9',
  'UA.KH': '10',
  'UA.LH': '11',
  'UA.LV': '12',
  'UA.MY': '13',
  'UA.OD': '14',
  'UA.PL': '15',
  'UA.RV': '16',
  'UA.SM': '17',
  'UA.TP': '18',
  'UA.KK': '19',
  'UA.KS': '20',
  'UA.KM': '21',
  'UA.CK': '22',
  'UA.CV': '23',
  'UA.CH': '24',
  'UA.KC': '25',
  'UA.KR': '26',
  'UA.SC': '27',
};

/// Serializable parse output for [compute].
Map<String, dynamic> parseUkraineOblastGeoJsonString(String raw) {
  final decoded = jsonDecode(raw) as Map<String, dynamic>;
  final features = decoded['features'] as List<dynamic>;

  final centroids = <String, List<double>>{};
  final borderRings = <Map<String, dynamic>>[];

  for (final f in features) {
    final feat = f as Map<String, dynamic>;
    final props = feat['properties'] as Map<String, dynamic>?;
    if (props == null) continue;
    final hasc = props['HASC_1'] as String?;
    if (hasc == null || hasc == '?' || !kHascToHeatmapStateId.containsKey(hasc)) {
      continue;
    }
    final stateId = kHascToHeatmapStateId[hasc]!;
    final geom = feat['geometry'] as Map<String, dynamic>?;
    if (geom == null) continue;

    double sumLat = 0, sumLng = 0, wSum = 0;
    for (final ring in _exteriorRings(geom)) {
      if (ring.length < 3) continue;
      double rl = 0, rg = 0;
      for (final p in ring) {
        final pair = p as List<dynamic>;
        final lng = (pair[0] as num).toDouble();
        final lat = (pair[1] as num).toDouble();
        rl += lat;
        rg += lng;
      }
      final n = ring.length.toDouble();
      final clat = rl / n;
      final clng = rg / n;
      sumLat += clat * n;
      sumLng += clng * n;
      wSum += n;

      borderRings.add({
        'stateId': stateId,
        'ring': ring
            .map((p) {
              final pair = p as List<dynamic>;
              return [pair[0] as num, pair[1] as num];
            })
            .toList(),
      });
    }
    if (wSum > 0) {
      centroids[stateId] = [sumLat / wSum, sumLng / wSum];
    }
  }

  return {'centroids': centroids, 'borderRings': borderRings};
}

/// Ramer–Douglas–Peucker in lat/lng space (degrees). Reduces vertex count for map performance.
List<LatLng> _simplifyRingRdp(List<LatLng> points, double epsilonDeg) {
  if (points.length < 3 || epsilonDeg <= 0) return List<LatLng>.from(points);

  final n = points.length;
  final keep = List<bool>.filled(n, false);
  keep[0] = true;
  keep[n - 1] = true;
  final stack = <List<int>>[
    [0, n - 1],
  ];

  while (stack.isNotEmpty) {
    final range = stack.removeLast();
    final start = range[0];
    final end = range[1];
    var maxDist = 0.0;
    var maxIdx = start;
    final a = points[start];
    final b = points[end];
    for (var i = start + 1; i < end; i++) {
      final d = _perpendicularDistanceDeg(points[i], a, b);
      if (d > maxDist) {
        maxDist = d;
        maxIdx = i;
      }
    }
    if (maxDist > epsilonDeg) {
      keep[maxIdx] = true;
      stack.add([start, maxIdx]);
      stack.add([maxIdx, end]);
    }
  }

  final out = <LatLng>[];
  for (var i = 0; i < n; i++) {
    if (keep[i]) out.add(points[i]);
  }
  return out.length >= 3 ? out : List<LatLng>.from(points);
}

double _perpendicularDistanceDeg(LatLng p, LatLng a, LatLng b) {
  final x0 = p.longitude;
  final y0 = p.latitude;
  final x1 = a.longitude;
  final y1 = a.latitude;
  final x2 = b.longitude;
  final y2 = b.latitude;
  var dx = x2 - x1;
  var dy = y2 - y1;
  if (dx == 0 && dy == 0) {
    return math.sqrt(
      math.pow(x0 - x1, 2) + math.pow(y0 - y1, 2),
    );
  }
  final t = ((x0 - x1) * dx + (y0 - y1) * dy) / (dx * dx + dy * dy);
  final tClamped = t.clamp(0.0, 1.0);
  final projX = x1 + tClamped * dx;
  final projY = y1 + tClamped * dy;
  return math.sqrt(
    math.pow(x0 - projX, 2) + math.pow(y0 - projY, 2),
  );
}

/// Ring simplification for boundaries (polylines). Coarser than polygon-fill needs.
const double kHeatmapOblastSimplifyEpsilonDeg = 0.0045;

List<List<dynamic>> _exteriorRings(Map<String, dynamic> geom) {
  final type = geom['type'] as String?;
  final coords = geom['coordinates'];
  if (type == null || coords == null) return [];

  if (type == 'Polygon') {
    final rings = coords as List<dynamic>;
    if (rings.isEmpty) return [];
    return [rings[0] as List<dynamic>];
  }
  if (type == 'MultiPolygon') {
    final polys = coords as List<dynamic>;
    final out = <List<dynamic>>[];
    for (final poly in polys) {
      final rings = poly as List<dynamic>;
      if (rings.isNotEmpty) out.add(rings[0] as List<dynamic>);
    }
    return out;
  }
  return [];
}

/// One exterior ring belonging to an oblast (id `1`…`27`).
class OblastGeoRing {
  const OblastGeoRing({required this.oblastStateId, required this.points});

  final String oblastStateId;
  final List<LatLng> points;
}

/// Centroids + oblast outlines in real lat/lng (from `assets/geo/ukraine_oblasts.geojson`).
class UkraineOblastGeoData {
  UkraineOblastGeoData._({
    required this.centroidByOblastStateId,
    required this.oblastRings,
  });

  final Map<String, LatLng> centroidByOblastStateId;
  final List<OblastGeoRing> oblastRings;

  static UkraineOblastGeoData? _cached;
  static const int _cacheSchema = 4; // bump when simplification / rings change
  static int? _cachedSchema;

  static Future<UkraineOblastGeoData> load() async {
    if (_cached != null && _cachedSchema == _cacheSchema) return _cached!;
    final raw = await rootBundle.loadString('assets/geo/ukraine_oblasts.geojson');
    final parsed = await compute(parseUkraineOblastGeoJsonString, raw);
    final centroidsRaw = parsed['centroids'] as Map<String, dynamic>;
    final centroidByOblastStateId = centroidsRaw.map((k, v) {
      final pair = v as List<dynamic>;
      return MapEntry(
        k,
        LatLng((pair[0] as num).toDouble(), (pair[1] as num).toDouble()),
      );
    });

    final rings = parsed['borderRings'] as List<dynamic>;
    final oblastRings = <OblastGeoRing>[];
    for (final item in rings) {
      final m = item as Map<String, dynamic>;
      final stateId = m['stateId'] as String?;
      final ring = m['ring'] as List<dynamic>?;
      if (stateId == null || ring == null || ring.length < 3) continue;
      final raw = ring
          .map((p) {
            final pair = p as List<dynamic>;
            return LatLng(
              (pair[1] as num).toDouble(),
              (pair[0] as num).toDouble(),
            );
          })
          .toList();
      oblastRings.add(
        OblastGeoRing(
          oblastStateId: stateId,
          points: _simplifyRingRdp(raw, kHeatmapOblastSimplifyEpsilonDeg),
        ),
      );
    }

    _cached = UkraineOblastGeoData._(
      centroidByOblastStateId: centroidByOblastStateId,
      oblastRings: oblastRings,
    );
    _cachedSchema = _cacheSchema;
    return _cached!;
  }

  /// Oblast outlines as closed [Polyline]s (no polygon tessellation — stable on zoom).
  List<Polyline<Object>> oblastBoundaryPolylines({
    required Color color,
    double strokeWidth = 1.0,
  }) {
    return oblastRings.map((r) {
      final pts = List<LatLng>.from(r.points);
      if (pts.isNotEmpty) {
        final a = pts.first;
        final b = pts.last;
        if (a.latitude != b.latitude || a.longitude != b.longitude) {
          pts.add(a);
        }
      }
      return Polyline<Object>(
        points: pts,
        color: color,
        strokeWidth: strokeWidth,
        strokeCap: StrokeCap.round,
        strokeJoin: StrokeJoin.round,
      );
    }).toList();
  }
}

/// Max value in [counts] (0 if empty).
int heatmapMaxCount(Map<String, int> counts) {
  var m = 0;
  for (final c in counts.values) {
    if (c > m) m = c;
  }
  return m;
}

/// Semi-transparent color for heat circles / legend (neutral tint when no events).
Color heatmapOblastFillColor(
  String oblastStateId,
  Map<String, int> countsByOblastStateId,
  bool isDark,
) {
  final maxCount = heatmapMaxCount(countsByOblastStateId);
  final count = countsByOblastStateId[oblastStateId] ?? 0;
  if (maxCount <= 0 || count <= 0) {
    return isDark
        ? const Color(0xFF475569).withValues(alpha: 0.14)
        : const Color(0xFFCBD5E1).withValues(alpha: 0.22);
  }
  final t = math.sqrt(count / maxCount).clamp(0.0, 1.0);
  const cold = Color(0xFF0891B2);
  const warm = Color(0xFFFBBF24);
  const hot = Color(0xFFDC2626);
  late final Color core;
  if (t < 0.45) {
    core = Color.lerp(cold, warm, t / 0.45)!;
  } else {
    core = Color.lerp(warm, hot, (t - 0.45) / 0.55)!;
  }
  final a = 0.42 + 0.48 * t;
  return core.withValues(alpha: a);
}
