import 'package:flutter_test/flutter_test.dart';
import 'package:neptun_alarm_app/services/legacy_region_name_match.dart';

void main() {
  group('legacyNameRegionMatches', () {
    test('Київ (місто) не має бачити Київську область у region', () {
      expect(
        legacyNameRegionMatches('м. Київ', 'Київська область', 'Буча'),
        isFalse,
      );
      expect(
        legacyNameRegionMatches('Київ', 'Київська область', 'Біла Церква'),
        isFalse,
      );
    });

    test('обрана Київська обл. — треба проходити по назві region', () {
      expect(
        legacyNameRegionMatches('Київська область', 'Київська область', 'x'),
        isTrue,
      );
    });

    test('тривога по місту в location для обраного Київ (коротка назва)', () {
      expect(
        legacyNameRegionMatches('Київ', 'Що завгодно', 'м. Київ — тривога'),
        isTrue,
      );
    });
  });
}
