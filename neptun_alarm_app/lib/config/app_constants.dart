import 'package:flutter/material.dart';

/// Централізовані константи додатку
class AppConstants {
  AppConstants._();

  // ===== Версія додатку =====
  static const String appVersion = '2.1.1';
  static const int appBuildNumber = 47;
  static const String appName = 'Dron Alerts';

  /// Текст ціни PRO на paywall (одноразова покупка). Фактичне списання — за тарифом Apple/Google.
  static const String premiumDisplayPrice = '150 грн назавжди';

  /// Посилання на сторінки магазинів (fallback, якщо сервер не повернув свої URL).
  static const String playStoreListingUrl =
      'https://play.google.com/store/apps/details?id=com.neptunalarm.neptun_alarm_app';
  static const String appStoreListingUrl =
      'https://apps.apple.com/app/id6743895428';

  // ===== Таймери та інтервали =====
  static const Duration onlineCheckInterval = Duration(seconds: 30);

  /// Як на сайті (`PRESENCE_INTERVAL`) — активний додаток.
  static const Duration presencePingInterval = Duration(minutes: 5);
  /// Додаток у фоні — рідший пінг, але сесія лишається в «онлайн».
  static const Duration presenceBackgroundPingInterval = Duration(minutes: 2);

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

  /// Підсвітка активного пункту [TacticalNavBar] (без різкої зміни фону/шрифту).
  static const Duration bottomNavSelectionDuration = Duration(milliseconds: 240);

  /// Перехід світла / темна тема — збігається з [MaterialApp.themeAnimationStyle].
  static const Duration themeSwitchDuration = Duration(milliseconds: 780);
  static const Curve themeSwitchCurve = Curves.easeInOutCubicEmphasized;

  // ===== Threat icon sizes =====
  static const int threatIconSize = 64;
  static const double threatIconDisplaySize = 7.0;
}
