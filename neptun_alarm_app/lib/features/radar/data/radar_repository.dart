import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../../../config/api_config.dart';
import '../domain/radar_snapshot.dart';
import 'radar_snapshot_cache.dart';

/// REST для вкладки «Радар» ([ApiConfig.threats], [ApiConfig.alarmStatus]).
class RadarRepository {
  RadarRepository({RadarSnapshotCache? cache})
      : _cache = cache ?? RadarSnapshotCache();

  final RadarSnapshotCache _cache;

  Future<RadarSnapshot> fetchSnapshot({required int historyMinutes}) async {
    try {
      final snap = await _fetchFromNetwork(historyMinutes: historyMinutes);
      await _cache.save(snap);
      return snap;
    } catch (_) {
      final cached = await _cache.load();
      if (cached != null) return cached;
      rethrow;
    }
  }

  Future<RadarSnapshot> _fetchFromNetwork({
    required int historyMinutes,
  }) async {
    final threatsUrl = '${ApiConfig.threats}?timeRange=$historyMinutes';

    final responses = await Future.wait([
      http.get(Uri.parse(threatsUrl)).timeout(ApiConfig.httpTimeout),
      http.get(Uri.parse(ApiConfig.alarmStatus)).timeout(ApiConfig.httpTimeout),
    ]);

    List<Map<String, dynamic>> markers = [];
    if (responses[0].statusCode == 200) {
      final raw = parseThreatsEnvelope(jsonDecode(responses[0].body));
      markers = raw.map(normalizeThreatMarker).toList();
    } else if (responses[0].statusCode != 200) {
      throw Exception('threats HTTP ${responses[0].statusCode}');
    }

    var active = 0;
    if (responses[1].statusCode == 200) {
      final alarm = jsonDecode(responses[1].body);
      final alerts = alarm['alerts'];
      active = alerts is Map ? alerts.length : 0;
    }

    return RadarSnapshot(
      markers: markers,
      activeOblastsUnderAlarm: active,
      fetchedAt: DateTime.now(),
    );
  }

  /// Нормалізація V10 полів API для UI.
  @visibleForTesting
  static Map<String, dynamic> normalizeThreatMarker(Map<String, dynamic> raw) {
    final m = Map<String, dynamic>.from(raw);
    final pi = m['predicted_impact'] ?? m['predictedImpact'];
    if (pi is Map) {
      m['predicted_impact'] = Map<String, dynamic>.from(pi);
    }
    m['track_quality_score'] ??=
        m['trackQualityScore'] ?? m['quality_score'] ?? m['qualityScore'];
    m['formation_id'] ??= m['formationId'] ?? m['wave_id'] ?? m['waveId'];
    if (m['maneuver_detected'] == null) {
      m['maneuver_detected'] = m['maneuverDetected'] == true;
    }
    m['impact_zone_km'] ??= m['impactZoneKm'];
    return m;
  }

  /// Для юніт-тестів (формат тіла `/api/threats`).
  @visibleForTesting
  static List<Map<String, dynamic>> parseThreatsEnvelope(dynamic decoded) {
    if (decoded is List) {
      return decoded.cast<Map<String, dynamic>>();
    }
    if (decoded is Map) {
      if (decoded['threats'] is List) {
        return (decoded['threats'] as List).cast<Map<String, dynamic>>();
      }
      if (decoded['markers'] is List) {
        return (decoded['markers'] as List).cast<Map<String, dynamic>>();
      }
    }
    return [];
  }

  /// Кількість рядків з непустим `activeAlerts` у payload SSE / alarm list.
  static int countActiveRegionsFromAlarmStream(List<dynamic> rows) {
    var count = 0;
    for (final r in rows) {
      if (r is Map && (r['activeAlerts'] as List?)?.isNotEmpty == true) {
        count++;
      }
    }
    return count;
  }
}
