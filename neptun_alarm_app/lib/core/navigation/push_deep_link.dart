import 'package:go_router/go_router.dart';

import '../router/route_paths.dart';

/// Maps FCM / local notification payload → GoRouter location.
abstract final class PushDeepLink {
  PushDeepLink._();

  static String routeFromData(Map<String, dynamic> data) {
    final action = (data['action'] ?? data['type'] ?? data['screen'] ?? '')
        .toString()
        .toLowerCase()
        .trim();

    switch (action) {
      case 'open_chat':
      case 'chat':
      case 'message':
        return RoutePaths.chat;
      case 'open_radar':
      case 'radar':
      case 'threat':
      case 'track':
        return RoutePaths.radar;
      case 'open_alerts':
      case 'alerts':
      case 'regions':
      case 'region':
        return RoutePaths.alerts;
      case 'open_map':
      case 'map':
      case 'threat_marker':
        return RoutePaths.home;
      case 'radar_full':
      case 'dashboard':
        return RoutePaths.radarFull;
      case 'briefing':
        return RoutePaths.briefing;
      case 'sos':
        return RoutePaths.home;
      default:
        break;
    }

    if (data['track_id'] != null ||
        data['lat'] != null ||
        data['lng'] != null ||
        data['threat_type'] != null) {
      return RoutePaths.home;
    }

    return RoutePaths.home;
  }

  static void navigate(GoRouter router, Map<String, dynamic> data) {
    router.go(routeFromData(data));
  }

  /// `neptun://alarm?open=radar` from home screen widget.
  static String? redirectFromWidgetUri(Uri uri) {
    if (uri.scheme != 'neptun') return null;
    final open = uri.queryParameters['open']?.toLowerCase();
    return switch (open) {
      'radar' => RoutePaths.radar,
      'chat' => RoutePaths.chat,
      'alerts' || 'regions' => RoutePaths.alerts,
      'map' || null => RoutePaths.home,
      _ => RoutePaths.home,
    };
  }
}
