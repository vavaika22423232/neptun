import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../../../config/api_config.dart';
import '../domain/radar_snapshot.dart';

/// REST для вкладки «Радар» ([ApiConfig.threats], [ApiConfig.alarmStatus]).
class RadarRepository {
  Future<RadarSnapshot> fetchSnapshot({required int historyMinutes}) async {
    final threatsUrl = '${ApiConfig.threats}?timeRange=$historyMinutes';

    final responses = await Future.wait([
      http.get(Uri.parse(threatsUrl)).timeout(ApiConfig.httpTimeout),
      http.get(Uri.parse(ApiConfig.alarmStatus)).timeout(ApiConfig.httpTimeout),
    ]);

    List<Map<String, dynamic>> markers = [];
    if (responses[0].statusCode == 200) {
      markers = parseThreatsEnvelope(jsonDecode(responses[0].body));
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
