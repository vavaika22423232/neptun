import 'package:flutter_test/flutter_test.dart';
import 'package:neptun_alarm_app/core/router/app_redirect.dart';
import 'package:neptun_alarm_app/core/router/route_paths.dart';

void main() {
  group('resolveAppRedirect', () {
    test('/regions → /alerts when onboarding complete', () {
      expect(
        resolveAppRedirect(
          isFirstLaunch: false,
          location: '/regions',
          uri: Uri.parse('/regions'),
        ),
        RoutePaths.alerts,
      );
    });

    test('first launch → onboarding', () {
      expect(
        resolveAppRedirect(
          isFirstLaunch: true,
          location: '/',
          uri: Uri.parse('/'),
        ),
        RoutePaths.onboarding,
      );
    });

    test('widget deep link → radar', () {
      expect(
        resolveAppRedirect(
          isFirstLaunch: false,
          location: '/',
          uri: Uri.parse('neptun://alarm?open=radar'),
        ),
        RoutePaths.radar,
      );
    });
  });
}
