import 'package:flutter_test/flutter_test.dart';
import 'package:neptun_alarm_app/features/radar/domain/radar_quick_filter.dart';

void main() {
  group('RadarQuickFilter', () {
    test('all matches any non-empty type', () {
      expect(
        RadarQuickFilter.all.matchesMarker({'threatType': 'shahed'}),
        isTrue,
      );
    });

    test('shahedLayer groups drones and fpv', () {
      expect(
        RadarQuickFilter.shahedLayer.matchesMarker({'type': 'shahed'}),
        isTrue,
      );
      expect(
        RadarQuickFilter.shahedLayer.matchesMarker({'threat_type': 'fpv'}),
        isTrue,
      );
      expect(
        RadarQuickFilter.shahedLayer.matchesMarker({'threatType': 'raketa'}),
        isFalse,
      );
    });

    test('missiles includes ballistic and kab', () {
      for (final t in ['ballistic', 'kab', 'raketa', 'rszv']) {
        expect(
          RadarQuickFilter.missiles.matchesMarker({'threatType': t}),
          isTrue,
          reason: t,
        );
      }
      expect(
        RadarQuickFilter.missiles.matchesMarker({'threatType': 'avia'}),
        isFalse,
      );
    });

    test('empty type key never matches narrow filters', () {
      expect(
        RadarQuickFilter.blasts.matchesMarker({'place': 'Kyiv'}),
        isFalse,
      );
    });
  });
}
