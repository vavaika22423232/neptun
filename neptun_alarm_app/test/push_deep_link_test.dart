import 'package:flutter_test/flutter_test.dart';
import 'package:neptun_alarm_app/core/navigation/push_deep_link.dart';
import 'package:neptun_alarm_app/core/router/route_paths.dart';

void main() {
  group('PushDeepLink.routeFromData', () {
    test('open_chat → chat tab', () {
      expect(
        PushDeepLink.routeFromData({'action': 'open_chat'}),
        RoutePaths.chat,
      );
    });

    test('open_radar → radar tab', () {
      expect(
        PushDeepLink.routeFromData({'type': 'radar'}),
        RoutePaths.radar,
      );
    });

    test('regions → alerts', () {
      expect(
        PushDeepLink.routeFromData({'action': 'regions'}),
        RoutePaths.alerts,
      );
    });

    test('track_id defaults to map', () {
      expect(
        PushDeepLink.routeFromData({'track_id': 'abc'}),
        RoutePaths.home,
      );
    });
  });

  group('PushDeepLink.redirectFromWidgetUri', () {
    test('neptun://alarm?open=radar', () {
      expect(
        PushDeepLink.redirectFromWidgetUri(
          Uri.parse('neptun://alarm?open=radar'),
        ),
        RoutePaths.radar,
      );
    });
  });
}
