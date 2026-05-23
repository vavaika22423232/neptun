import '../navigation/push_deep_link.dart';
import 'route_paths.dart';

/// Логіка redirect для GoRouter (винесено для тестів).
String? resolveAppRedirect({
  required bool isFirstLaunch,
  required String location,
  required Uri uri,
}) {
  if (isFirstLaunch && location != RoutePaths.onboarding) {
    return RoutePaths.onboarding;
  }
  if (!isFirstLaunch && location == RoutePaths.onboarding) {
    return RoutePaths.home;
  }
  if (location == '/regions') return RoutePaths.alerts;

  return PushDeepLink.redirectFromWidgetUri(uri);
}
