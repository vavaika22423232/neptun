/// Централізовані константи додатку
class AppConstants {
  AppConstants._();

  // ===== Версія додатку =====
  static const String appVersion = '2.0.1';
  static const int appBuildNumber = 40;
  static const String appName = 'NEPTUN';

  // ===== Таймери та інтервали =====
  static const Duration onlineCheckInterval = Duration(seconds: 30);
  static const Duration alarmCheckInterval = Duration(minutes: 1);
  static const Duration chatRefreshInterval = Duration(seconds: 10);
  static const Duration bannerCheckInterval = Duration(seconds: 2);
  static const int maxBannerCheckAttempts = 15;

  // ===== Review =====
  static const int minLaunchesForReview = 5;
  static const int minDaysForReview = 3;

  // ===== Chat =====
  static const int maxMessageLength = 500;
  static const int maxNicknameLength = 20;
  static const int minNicknameLength = 2;

  // ===== Map =====
  static const double defaultMapZoom = 6.0;
  static const double minMapZoom = 4.0;
  static const double maxMapZoom = 10.0;
  static const double ukraineLatitude = 48.5;
  static const double ukraineLongitude = 31.0;

  // ===== Animations =====
  static const Duration shortAnimation = Duration(milliseconds: 150);
  static const Duration mediumAnimation = Duration(milliseconds: 300);
  static const Duration longAnimation = Duration(milliseconds: 500);

  // ===== Threat icon sizes =====
  static const int threatIconSize = 64;
  static const double threatIconDisplaySize = 7.0;
}
