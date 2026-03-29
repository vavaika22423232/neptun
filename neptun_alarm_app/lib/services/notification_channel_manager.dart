import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

/// Керування notification channels з правильною вібрацією
/// 
/// ВАЖЛИВО: Android кешує налаштування каналу при створенні.
/// Тому використовуємо РІЗНІ канали для режимів з/без вібрації.
class NotificationChannelManager {
  static final NotificationChannelManager _instance = NotificationChannelManager._internal();
  factory NotificationChannelManager() => _instance;
  NotificationChannelManager._internal();

  final FlutterLocalNotificationsPlugin _notifications = FlutterLocalNotificationsPlugin();
  
  bool _isInitialized = false;

  // === CHANNEL IDs ===
  // Кожен тип має два варіанти: з вібрацією та без
  
  // Critical alerts (ракети, балістика)
  static const String criticalVibrate = 'alerts_critical_vibrate';
  static const String criticalSilent = 'alerts_critical_silent';
  
  // Normal alerts (дрони, загальна тривога)
  static const String normalVibrate = 'alerts_normal_vibrate';
  static const String normalSilent = 'alerts_normal_silent';
  
  // All clear (відбій)
  static const String allClearVibrate = 'alerts_allclear_vibrate';
  static const String allClearSilent = 'alerts_allclear_silent';

  /// Ініціалізація каналів
  Future<void> initialize() async {
    if (_isInitialized) return;
    if (!Platform.isAndroid) {
      _isInitialized = true;
      return;
    }

    try {
      final androidPlugin = _notifications.resolvePlatformSpecificImplementation<
          AndroidFlutterLocalNotificationsPlugin>();
      
      if (androidPlugin == null) {
        debugPrint('⚠️ Android plugin not available');
        return;
      }

      // Critical channels
      await androidPlugin.createNotificationChannel(
        const AndroidNotificationChannel(
          criticalVibrate,
          'Критичні тривоги',
          description: 'Ракетна небезпека, балістика',
          importance: Importance.max,
          playSound: true,
          enableVibration: true,
          enableLights: true,
        ),
      );
      
      await androidPlugin.createNotificationChannel(
        const AndroidNotificationChannel(
          criticalSilent,
          'Критичні тривоги (без вібро)',
          description: 'Ракетна небезпека, балістика',
          importance: Importance.max,
          playSound: true,
          enableVibration: false,
          enableLights: true,
        ),
      );

      // Normal channels
      await androidPlugin.createNotificationChannel(
        const AndroidNotificationChannel(
          normalVibrate,
          'Звичайні тривоги',
          description: 'БПЛА, загальна тривога',
          importance: Importance.high,
          playSound: true,
          enableVibration: true,
          enableLights: true,
        ),
      );
      
      await androidPlugin.createNotificationChannel(
        const AndroidNotificationChannel(
          normalSilent,
          'Звичайні тривоги (без вібро)',
          description: 'БПЛА, загальна тривога',
          importance: Importance.high,
          playSound: true,
          enableVibration: false,
          enableLights: true,
        ),
      );

      // All clear channels
      await androidPlugin.createNotificationChannel(
        const AndroidNotificationChannel(
          allClearVibrate,
          'Відбій тривоги',
          description: 'Повідомлення про відбій',
          importance: Importance.high,
          playSound: true,
          enableVibration: true,
          enableLights: true,
        ),
      );
      
      await androidPlugin.createNotificationChannel(
        const AndroidNotificationChannel(
          allClearSilent,
          'Відбій тривоги (без вібро)',
          description: 'Повідомлення про відбій',
          importance: Importance.high,
          playSound: true,
          enableVibration: false,
          enableLights: true,
        ),
      );

      _isInitialized = true;
      debugPrint('✅ Notification channels initialized');
    } catch (e) {
      debugPrint('❌ Failed to create notification channels: $e');
    }
  }

  /// Отримати ID каналу для сповіщення
  /// [isCritical] - чи це критичне сповіщення (ракети/балістика)
  /// [isAllClear] - чи це відбій
  /// [vibrationEnabled] - чи увімкнена вібрація в налаштуваннях
  String getChannelId({
    required bool isCritical,
    required bool isAllClear,
    required bool vibrationEnabled,
  }) {
    if (isAllClear) {
      return vibrationEnabled ? allClearVibrate : allClearSilent;
    }
    
    if (isCritical) {
      return vibrationEnabled ? criticalVibrate : criticalSilent;
    }
    
    return vibrationEnabled ? normalVibrate : normalSilent;
  }

  /// Отримати назву каналу
  String getChannelName({
    required bool isCritical,
    required bool isAllClear,
    required bool vibrationEnabled,
  }) {
    final suffix = vibrationEnabled ? '' : ' (без вібро)';
    
    if (isAllClear) {
      return 'Відбій тривоги$suffix';
    }
    
    if (isCritical) {
      return 'Критичні тривоги$suffix';
    }
    
    return 'Звичайні тривоги$suffix';
  }
}
