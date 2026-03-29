import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:home_widget/home_widget.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'purchase_service.dart';

/// Сервіс для оновлення віджета на робочому столі Android
/// ТІЛЬКИ ДЛЯ PREMIUM КОРИСТУВАЧІВ
class WidgetService {
  static final WidgetService _instance = WidgetService._internal();
  factory WidgetService() => _instance;
  WidgetService._internal();

  static const String _androidWidgetName = 'NeptunWidgetProvider';
  static const String _iosWidgetName = 'NeptunWidget';
  static const String _appGroupId = 'group.com.neptunalarm.neptunAlarmApp';

  bool _isInitialized = false;

  /// Перевірка чи користувач має Premium
  bool get _isPremium => PurchaseService().isPremium;

  /// Ініціалізація сервісу
  Future<void> initialize() async {
    if (_isInitialized || !(Platform.isAndroid || Platform.isIOS)) return;

    try {
      if (Platform.isIOS) {
        await HomeWidget.setAppGroupId(_appGroupId);
      }

      if (Platform.isAndroid) {
        // Реєструємо callback для оновлення віджета
        HomeWidget.registerInteractivityCallback(backgroundCallback);
      }
      _isInitialized = true;
      debugPrint('WidgetService initialized');
    } catch (e) {
      debugPrint('WidgetService init error: $e');
    }
  }

  Future<void> _ensureAppGroupId() async {
    if (!Platform.isIOS) return;

    try {
      await HomeWidget.setAppGroupId(_appGroupId);
      _isInitialized = true;
    } catch (e) {
      debugPrint('WidgetService app group error: $e');
    }
  }

  /// Оновити дані віджета (ТІЛЬКИ PREMIUM)
  Future<void> updateWidget({
    required String region,
    required bool isAlarm,
    required int threatsCount,
    required int timerMinutes,
    int totalAlarms = 0,
    String threatType = '',
    int dronesCount = 0,
    int missilesCount = 0,
    int kabCount = 0,
    int ballisticCount = 0,
    int totalThreats = 0,
  }) async {
    if (!(Platform.isAndroid || Platform.isIOS)) return;

    await _ensureAppGroupId();

    // Перевірка Premium статусу
    if (!_isPremium) {
      await _showPremiumRequired();
      return;
    }

    try {
      // Очищаємо Premium повідомлення
      await HomeWidget.saveWidgetData<String?>('widget_status_text', null);
      
      // Зберігаємо дані для віджета
      await HomeWidget.saveWidgetData<String>('widget_region', region);
      await HomeWidget.saveWidgetData<bool>('widget_is_alarm', isAlarm);
      await HomeWidget.saveWidgetData<int>('widget_threats_count', threatsCount);
      await HomeWidget.saveWidgetData<int>('widget_timer_minutes', timerMinutes);
      await HomeWidget.saveWidgetData<int>('widget_total_alarms', totalAlarms);
      await HomeWidget.saveWidgetData<String>('widget_threat_type', threatType);
      
      // Детальна інформація про загрози
      await HomeWidget.saveWidgetData<int>('widget_drones_count', dronesCount);
      await HomeWidget.saveWidgetData<int>('widget_missiles_count', missilesCount);
      await HomeWidget.saveWidgetData<int>('widget_kab_count', kabCount);
      await HomeWidget.saveWidgetData<int>('widget_ballistic_count', ballisticCount);
      await HomeWidget.saveWidgetData<int>('widget_total_threats', totalThreats);
      
      await HomeWidget.saveWidgetData<int>('widget_last_update', DateTime.now().millisecondsSinceEpoch);

      // Оновлюємо віджет
      await HomeWidget.updateWidget(
        name: Platform.isIOS ? _iosWidgetName : _androidWidgetName,
        androidName: _androidWidgetName,
        iOSName: _iosWidgetName,
      );
      debugPrint('Widget updated: region=$region, alarm=$isAlarm, drones=$dronesCount, missiles=$missilesCount, kab=$kabCount');
    } catch (e) {
      debugPrint('Widget update error: $e');
    }
  }

  /// Оновити тільки статус тривоги
  Future<void> updateAlarmStatus({
    required bool isAlarm,
    String? region,
    int totalAlarms = 0,
    String threatType = '',
  }) async {
    if (!(Platform.isAndroid || Platform.isIOS)) return;

    await _ensureAppGroupId();

    try {
      await HomeWidget.saveWidgetData<bool>('widget_is_alarm', isAlarm);
      if (region != null) {
        await HomeWidget.saveWidgetData<String>('widget_region', region);
      }
      await HomeWidget.saveWidgetData<int>('widget_total_alarms', totalAlarms);
      await HomeWidget.saveWidgetData<String>('widget_threat_type', threatType);
      await HomeWidget.saveWidgetData<int>('widget_last_update', DateTime.now().millisecondsSinceEpoch);

      await HomeWidget.updateWidget(
        name: Platform.isIOS ? _iosWidgetName : _androidWidgetName,
        androidName: _androidWidgetName,
        iOSName: _iosWidgetName,
      );
    } catch (e) {
      debugPrint('Widget alarm update error: $e');
    }
  }

  /// Оновити кількість загроз
  Future<void> updateThreatsCount(int count) async {
    if (!(Platform.isAndroid || Platform.isIOS)) return;

    await _ensureAppGroupId();

    try {
      await HomeWidget.saveWidgetData<int>('widget_threats_count', count);
      await HomeWidget.saveWidgetData<int>('widget_last_update', DateTime.now().millisecondsSinceEpoch);

      await HomeWidget.updateWidget(
        name: Platform.isIOS ? _iosWidgetName : _androidWidgetName,
        androidName: _androidWidgetName,
        iOSName: _iosWidgetName,
      );
    } catch (e) {
      debugPrint('Widget threats update error: $e');
    }
  }

  /// Оновити таймер тривоги
  Future<void> updateTimer(int minutes) async {
    if (!(Platform.isAndroid || Platform.isIOS)) return;

    await _ensureAppGroupId();

    try {
      await HomeWidget.saveWidgetData<int>('widget_timer_minutes', minutes);
      await HomeWidget.saveWidgetData<int>('widget_last_update', DateTime.now().millisecondsSinceEpoch);

      await HomeWidget.updateWidget(
        name: Platform.isIOS ? _iosWidgetName : _androidWidgetName,
        androidName: _androidWidgetName,
        iOSName: _iosWidgetName,
      );
    } catch (e) {
      debugPrint('Widget timer update error: $e');
    }
  }

  /// Встановити регіон користувача
  Future<void> setUserRegion(String region) async {
    if (!(Platform.isAndroid || Platform.isIOS)) return;

    await _ensureAppGroupId();

    try {
      await HomeWidget.saveWidgetData<String>('widget_region', region);
      
      // Також зберігаємо в SharedPreferences
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('widget_user_region', region);

      await HomeWidget.updateWidget(
        name: Platform.isIOS ? _iosWidgetName : _androidWidgetName,
        androidName: _androidWidgetName,
        iOSName: _iosWidgetName,
      );
    } catch (e) {
      debugPrint('Widget region update error: $e');
    }
  }

  /// Отримати збережений регіон
  Future<String?> getUserRegion() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      return prefs.getString('widget_user_region');
    } catch (e) {
      return null;
    }
  }

  /// Скинути дані віджета
  Future<void> resetWidget() async {
    if (!(Platform.isAndroid || Platform.isIOS)) return;

    await _ensureAppGroupId();

    try {
      await HomeWidget.saveWidgetData<String>('widget_region', 'Оберіть регіон');
      await HomeWidget.saveWidgetData<bool>('widget_is_alarm', false);
      await HomeWidget.saveWidgetData<int>('widget_threats_count', 0);
      await HomeWidget.saveWidgetData<int>('widget_timer_minutes', 0);
      await HomeWidget.saveWidgetData<int>('widget_total_alarms', 0);
      await HomeWidget.saveWidgetData<String>('widget_threat_type', '');
      await HomeWidget.saveWidgetData<int>('widget_last_update', DateTime.now().millisecondsSinceEpoch);

      await HomeWidget.updateWidget(
        name: Platform.isIOS ? _iosWidgetName : _androidWidgetName,
        androidName: _androidWidgetName,
        iOSName: _iosWidgetName,
      );
    } catch (e) {
      debugPrint('Widget reset error: $e');
    }
  }

  /// Показати повідомлення про необхідність Premium
  Future<void> _showPremiumRequired() async {
    await _ensureAppGroupId();
    try {
      await HomeWidget.saveWidgetData<String>('widget_region', 'Premium');
      await HomeWidget.saveWidgetData<bool>('widget_is_alarm', false);
      await HomeWidget.saveWidgetData<String>('widget_status_text', 'Придбайте Premium');
      await HomeWidget.saveWidgetData<int>('widget_total_alarms', 0);
      await HomeWidget.saveWidgetData<int>('widget_last_update', DateTime.now().millisecondsSinceEpoch);

      await HomeWidget.updateWidget(
        name: Platform.isIOS ? _iosWidgetName : _androidWidgetName,
        androidName: _androidWidgetName,
        iOSName: _iosWidgetName,
      );
      debugPrint('Widget: Premium required message shown');
    } catch (e) {
      debugPrint('Widget premium message error: $e');
    }
  }
}

/// Background callback для обробки кліків на віджеті
@pragma('vm:entry-point')
Future<void> backgroundCallback(Uri? uri) async {
  if (uri?.host == 'open_app') {
    // Відкриваємо додаток (handled by Android intent)
  }
}
