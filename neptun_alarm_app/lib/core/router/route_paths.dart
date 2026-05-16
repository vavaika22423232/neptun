/// Єдиний реєстр маршрутів GoRouter (без повторень рядкових літералів).
abstract final class RoutePaths {
  RoutePaths._();

  static const String home = '/';
  static const String onboarding = '/onboarding';
  static const String radar = '/radar';
  static const String chat = '/chat';
  static const String profile = '/profile';
  static const String alerts = '/alerts';

  /// Регіони усередині вкладки «Радар» (query для GoRouter).
  static const String radarRegionsView = '/radar?view=regions';

  static const String premium = '/premium';
  static const String feedback = '/feedback';
  static const String feedbackModeration = '/feedback-moderation';
  static const String admin = '/admin';
  static const String chatAdmin = '/chat-admin';
  static const String complaints = '/complaints';
  static const String shelters = '/shelters';
  static const String safety = '/safety';
  static const String trust = '/trust';
  static const String history = '/history';
  static const String analytics = '/analytics';
  static const String heatmap = '/heatmap';
  static const String radarFull = '/radar-full';
  static const String briefing = '/briefing';
}
