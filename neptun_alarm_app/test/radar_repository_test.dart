import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:neptun_alarm_app/features/radar/data/radar_repository.dart';

void main() {
  group('RadarRepository.parseThreatsEnvelope', () {
    test('top-level JSON array', () {
      final out = RadarRepository.parseThreatsEnvelope([
        {'id': 'a', 'threatType': 'shahed'},
      ]);
      expect(out.length, 1);
      expect(out.first['threatType'], 'shahed');
    });

    test('map with threats key', () {
      final raw = jsonDecode(
        '{"threats":[{"id":"1","type":"raketa"}]}',
      );
      final out = RadarRepository.parseThreatsEnvelope(raw);
      expect(out.length, 1);
      expect(out.first['type'], 'raketa');
    });

    test('map with markers key', () {
      final raw = {'markers': <Map<String, Object>>[]};
      expect(RadarRepository.parseThreatsEnvelope(raw), isEmpty);
    });

    test('unsupported shape returns empty', () {
      expect(RadarRepository.parseThreatsEnvelope('x'), isEmpty);
    });
  });

  group('RadarRepository.normalizeThreatMarker', () {
    test('maps V10 snake_case fields', () {
      final out = RadarRepository.normalizeThreatMarker({
        'id': 't1',
        'trackQualityScore': 0.82,
        'formationId': 'wave-7',
        'maneuverDetected': true,
        'predictedImpact': {'eta_minutes': 12},
      });
      expect(out['track_quality_score'], 0.82);
      expect(out['formation_id'], 'wave-7');
      expect(out['maneuver_detected'], isTrue);
      expect(out['predicted_impact'], isA<Map>());
    });
  });

  group('RadarRepository.countActiveRegionsFromAlarmStream', () {
    test('counts rows with non-empty activeAlerts', () {
      final n = RadarRepository.countActiveRegionsFromAlarmStream([
        {'activeAlerts': ['a']},
        {'activeAlerts': []},
        {'region': 'x'},
      ]);
      expect(n, 1);
    });
  });
}
