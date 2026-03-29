import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'dart:math' as math;
import 'package:flutter_tts/flutter_tts.dart';
import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:uuid/uuid.dart';
import 'tts_service.dart';
import 'ballistic_alert_service.dart';
import 'live_activity_service.dart';
import 'widget_service.dart';
import 'sleep_mode_service.dart';
import '../models/notification_event.dart';
import '../models/user_region_selection.dart';
import 'notification_filter_service.dart';
import 'region_database.dart';
import 'alarm_tracking_service.dart';
import 'briefing_service.dart';
import 'package:go_router/go_router.dart';
import 'package:neptun_alarm_app/config/api_config.dart';
import 'package:neptun_alarm_app/config/prefs_keys.dart';
import 'package:neptun_alarm_app/core/di/service_locator.dart';
import 'package:neptun_alarm_app/core/pro/pro_features.dart';

// Track last notification to prevent duplicates (for foreground only)
String _lastNotificationKey = '';
int _lastNotificationTime = 0;

// Counter for unique notification IDs (prevents collision when multiple notifications arrive in same second)
int _notificationIdCounter = 0;

/// Generates a unique notification ID that won't collide
int _generateNotificationId() {
  // Combine timestamp with counter to ensure uniqueness
  // Use milliseconds and counter to handle multiple notifications per second
  final baseId =
      DateTime.now().millisecondsSinceEpoch %
      2147483647; // Keep within int32 range
  _notificationIdCounter = (_notificationIdCounter + 1) % 1000;
  return (baseId + _notificationIdCounter) % 2147483647;
}

class _DedupStore {
  static const String _notifKey = 'dedup_last_notification_key';
  static const String _notifTime = 'dedup_last_notification_time';
  static const String _ttsKey = 'dedup_last_tts_key';
  static const String _ttsTime = 'dedup_last_tts_time';

  static Future<bool> shouldSkipNotification(
    SharedPreferences prefs,
    String key, {
    int ttlMs = 30000,
  }) async {
    final lastKey = prefs.getString(_notifKey) ?? '';
    final lastTime = prefs.getInt(_notifTime) ?? 0;
    final now = DateTime.now().millisecondsSinceEpoch;
    if (key == lastKey && (now - lastTime) < ttlMs) {
      return true;
    }
    await prefs.setString(_notifKey, key);
    await prefs.setInt(_notifTime, now);
    return false;
  }

  static Future<bool> shouldSkipTts(
    SharedPreferences prefs,
    String key, {
    int ttlMs = 60000,
  }) async {
    final lastKey = prefs.getString(_ttsKey) ?? '';
    final lastTime = prefs.getInt(_ttsTime) ?? 0;
    final now = DateTime.now().millisecondsSinceEpoch;
    if (key == lastKey && (now - lastTime) < ttlMs) {
      return true;
    }
    await prefs.setString(_ttsKey, key);
    await prefs.setInt(_ttsTime, now);
    return false;
  }
}

class _NotificationMetrics {
  static const String _totalReceivedKey = 'notif_metrics_total_received';
  static const String _totalShownKey = 'notif_metrics_total_shown';
  static const String _totalSkippedKey = 'notif_metrics_total_skipped';
  static const String _lastReceivedAtKey = 'notif_metrics_last_received_at';

  static Future<void> trackReceived(SharedPreferences prefs) async {
    final current = prefs.getInt(_totalReceivedKey) ?? 0;
    await prefs.setInt(_totalReceivedKey, current + 1);
    await prefs.setInt(
      _lastReceivedAtKey,
      DateTime.now().millisecondsSinceEpoch,
    );
  }

  static Future<void> trackShown(SharedPreferences prefs) async {
    final current = prefs.getInt(_totalShownKey) ?? 0;
    await prefs.setInt(_totalShownKey, current + 1);
  }

  static Future<void> trackSkipped(SharedPreferences prefs) async {
    final current = prefs.getInt(_totalSkippedKey) ?? 0;
    await prefs.setInt(_totalSkippedKey, current + 1);
  }
}

class _NotificationContent {
  final String title;
  final String body;
  final String? subText;
  final bool isAllClear;
  final bool isRocket;
  final bool isDrone;
  final bool isKab;
  final bool isCritical;

  _NotificationContent({
    required this.title,
    required this.body,
    required this.subText,
    required this.isAllClear,
    required this.isRocket,
    required this.isDrone,
    required this.isKab,
    required this.isCritical,
  });
}

TimeOfDay _parseTimeOfDay(String value, TimeOfDay fallback) {
  final parts = value.split(':');
  if (parts.length != 2) return fallback;
  final hour = int.tryParse(parts[0]);
  final minute = int.tryParse(parts[1]);
  if (hour == null || minute == null) return fallback;
  return TimeOfDay(hour: hour.clamp(0, 23), minute: minute.clamp(0, 59));
}

bool _isWithinQuietHours(TimeOfDay now, TimeOfDay start, TimeOfDay end) {
  final nowMinutes = now.hour * 60 + now.minute;
  final startMinutes = start.hour * 60 + start.minute;
  final endMinutes = end.hour * 60 + end.minute;
  // If start == end, quiet hours are disabled (never quiet)
  if (startMinutes == endMinutes) return false;
  // Normal case: start < end (e.g., 08:00-18:00)
  if (startMinutes < endMinutes) {
    return nowMinutes >= startMinutes && nowMinutes < endMinutes;
  }
  // Overnight case: start > end (e.g., 22:00-07:00)
  return nowMinutes >= startMinutes || nowMinutes < endMinutes;
}

Future<bool> _shouldAllowByQuietHours(
  SharedPreferences prefs, {
  required bool isCritical,
}) async {
  final enabled = prefs.getBool('quiet_hours_enabled') ?? false;
  if (!enabled) return true;
  final allowCritical = prefs.getBool('quiet_hours_allow_critical') ?? true;
  if (isCritical && allowCritical) return true;
  final startRaw = prefs.getString('quiet_hours_start') ?? '22:00';
  final endRaw = prefs.getString('quiet_hours_end') ?? '07:00';
  final start = _parseTimeOfDay(startRaw, const TimeOfDay(hour: 22, minute: 0));
  final end = _parseTimeOfDay(endRaw, const TimeOfDay(hour: 7, minute: 0));
  final now = TimeOfDay.fromDateTime(DateTime.now());
  return !_isWithinQuietHours(now, start, end);
}

/// All Ukraine oblasts for auto-subscription on first launch
const List<String> _allUkraineOblasts = [
  'Харківська область',
  'Донецька область',
  'Запорізька область',
  'Херсонська область',
  'Луганська область',
  'Сумська область',
  'Дніпропетровська область',
  'Миколаївська область',
  'Одеська область',
  'Полтавська область',
  'Київська область',
  'Чернігівська область',
  'Черкаська область',
  'Кіровоградська область',
  'Вінницька область',
  'Житомирська область',
  'Рівненська область',
  'Волинська область',
  'Тернопільська область',
  'Хмельницька область',
  'Львівська область',
  'Івано-Франківська область',
  'Закарпатська область',
  'Чернівецька область',
  'м. Київ',
];

/// Завантажує ID-based вибір користувача з міграцією зі старого формату
Future<UserRegionSelection> _loadUserRegionSelection(
  SharedPreferences prefs,
) async {
  final Set<String> oblastIds =
      (prefs.getStringList('selected_oblast_ids') ?? []).toSet();
  final legacyOblastId = prefs.getString('selected_oblast_id');
  if (legacyOblastId != null && legacyOblastId.isNotEmpty) {
    oblastIds.add(legacyOblastId);
  }

  final Set<String> raionIds = (prefs.getStringList('selected_raion_ids') ?? [])
      .toSet();
  final String? settlementId = prefs.getString('selected_settlement_id');

  if (oblastIds.isEmpty && raionIds.isEmpty && settlementId == null) {
    final selectedRegions = prefs.getStringList('selected_regions') ?? [];
    if (selectedRegions.isNotEmpty) {
      final regionDb = RegionDatabase()..initialize();
      for (final name in selectedRegions) {
        final oblastId = regionDb.getOblastIdByName(name);
        if (oblastId != null) {
          oblastIds.add(oblastId);
          continue;
        }
        final raionId = regionDb.getRaionIdByName(name);
        if (raionId != null) {
          raionIds.add(raionId);
        }
      }

      if (oblastIds.isNotEmpty) {
        await prefs.setStringList('selected_oblast_ids', oblastIds.toList());
      }
      if (raionIds.isNotEmpty) {
        await prefs.setStringList('selected_raion_ids', raionIds.toList());
      }
    }
  }

  return UserRegionSelection(
    oblastIds: oblastIds,
    raionIds: raionIds,
    settlementId: settlementId,
  );
}

/// Форматує TTS повідомлення професійно та зрозуміло
/// Повертає готовий текст для озвучування
String _formatTtsMessage({
  required String region,
  required String location,
  required String threatType,
  required String alarmState,
  required String body,
}) {
  final lowerBody = body.toLowerCase();
  final lowerThreat = threatType.toLowerCase();

  // === ВІДБІЙ ТРИВОГИ ===
  if (alarmState == 'ended' ||
      lowerBody.contains('відбій') ||
      lowerBody.contains('знято') ||
      lowerThreat.contains('відбій')) {
    // Коротко та чітко - озвучуємо конкретне місце якщо є
    final place = _getPlaceName(location, region);
    return 'Відбій тривоги. $place.';
  }

  // === ТРИВОГА ===
  // Визначаємо місце (місто/район або область)
  final place = _getPlaceName(location, region);

  // Визначаємо тип загрози з body або threatType
  String threat = _detectThreatType(body, threatType);

  if (threat.isNotEmpty) {
    // Є конкретний тип загрози
    return 'Увага! $place. $threat.';
  } else {
    // Загальна тривога
    return 'Увага! $place. Повітряна тривога.';
  }
}

/// Отримує назву місця для озвучування
/// Пріоритет: конкретне місто > район > область
String _getPlaceName(String location, String region) {
  // Якщо є конкретна локація (місто) і вона відрізняється від області
  // Мінімум 5 символів для валідної локації (запобігає "Кам", "Хар" тощо)
  if (location.isNotEmpty &&
      location != region &&
      !location.toLowerCase().contains('область') &&
      location.length >= 5) {
    // Витягуємо місто з формату "Харків (Харківська обл.)"
    String city = location;
    if (location.contains('(')) {
      city = location.split('(').first.trim();
    }

    // Перевіряємо що витягнуте місто достатньо довге
    if (city.length < 5) {
      // Якщо місто занадто коротке, використовуємо регіон
      return _cleanRegionName(region);
    }

    // Додаємо область для контексту
    if (region.isNotEmpty && region.contains('область')) {
      return '$city, ${_cleanRegionName(region)}';
    }

    return city;
  }

  // Інакше повертаємо область
  return _cleanRegionName(region);
}

/// Визначає тип загрози з тексту повідомлення
String _detectThreatType(String body, String threatType) {
  final text = '$body $threatType'.toLowerCase();

  // Пріоритет: ракети > КАБи > БПЛА > вибухи > загальна тривога
  if (text.contains('балістичн') || text.contains('крилат')) {
    return 'Ракетна небезпека';
  }
  if (text.contains('ракет')) {
    return 'Загроза ракетного удару';
  }
  if (text.contains('каб')) {
    return 'Загроза застосування КАБів';
  }
  if (text.contains('бпла') ||
      text.contains('дрон') ||
      text.contains('шахед')) {
    return 'Загроза ударних БПЛА';
  }
  if (text.contains('вибух')) {
    return 'Повідомляють про вибухи';
  }
  if (text.contains('артилер')) {
    return 'Артилерійська загроза';
  }

  // Якщо threatType містить щось корисне і не generic
  if (threatType.isNotEmpty &&
      !threatType.toLowerCase().contains('повітряна тривога') &&
      threatType.length > 3) {
    return threatType;
  }

  return ''; // Загальна тривога - без конкретики
}

String _resolveThreatKey(String body, String threatType) {
  final text = '$body $threatType'.toLowerCase();
  if (text.contains('балістик') || text.contains('балистик')) {
    return 'ballistic';
  }
  if (text.contains('каб')) return 'kab';
  if (text.contains('ракет') || text.contains('крилат')) return 'rocket';
  if (text.contains('бпла') ||
      text.contains('дрон') ||
      text.contains('шахед')) {
    return 'drones';
  }
  if (text.contains('артилер') || text.contains('обстріл')) return 'artillery';
  if (text.contains('вибух')) return 'explosion';
  return 'air';
}

bool _isThreatTypeAllowed(SharedPreferences prefs, String threatKey) {
  final allowed = prefs.getStringList('notify_threat_types') ?? [];
  if (allowed.isEmpty) return true;
  return allowed.contains(threatKey);
}

/// Очищає назву регіону для кращого озвучування
String _cleanRegionName(String region) {
  if (region.isEmpty) return '';

  // Просто повертаємо регіон як є - він уже в правильному форматі
  // Наприклад: "Харківська область", "м. Київ", "Запорізька область"
  return region;
}

// Background message handler - MUST be top-level function
@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  // Ensure Firebase is initialized in the background isolate
  // (on iOS, the bg handler may run in a separate isolate where Firebase is not yet init'd)
  try {
    await Firebase.initializeApp();
  } catch (_) {
    // Already initialized — safe to ignore
  }

  // === ДЕТАЛЬНЕ ЛОГУВАННЯ ВСІХ FCM ПОВІДОМЛЕНЬ (BACKGROUND) ===
  debugPrint('📩📩📩 FCM MESSAGE RECEIVED (BACKGROUND) 📩📩📩');
  debugPrint('📩 messageId: ${message.messageId}');
  debugPrint('📩 from: ${message.from}');
  debugPrint('📩 data: ${message.data}');
  debugPrint('📩 data[type]: ${message.data['type']}');
  debugPrint('📩 notification?.title: ${message.notification?.title}');
  debugPrint('📩 notification?.body: ${message.notification?.body}');
  debugPrint('📩📩📩 END FCM MESSAGE (BACKGROUND) 📩📩📩');

  // ВАЖЛИВО: Перевіряємо чи сповіщення увімкнені
  final prefs = await SharedPreferences.getInstance();
  final notificationsEnabled = prefs.getBool('notifications_enabled') ?? true;

  if (!notificationsEnabled) {
    debugPrint('🔕 Notifications disabled - skipping background notification');
    return;
  }

  await _NotificationMetrics.trackReceived(prefs);

  final data = message.data;
  final title = data['title'] ?? message.notification?.title ?? 'Тривога';
  // FCM sends location in data['location'] or data['city'], body in data['body'] or notification.body
  final location =
      data['location'] ?? data['city'] ?? ''; // Specific place (city)
  final body =
      data['body'] ??
      message.notification?.body ??
      location; // Fallback to location
  final region = data['region'] ?? ''; // Oblast
  final threatType =
      data['threat_type'] ?? ''; // Threat type (БПЛА, ракети, etc.)
  final alarmState = data['alarm_state'] ?? '';
  final isCritical = data['is_critical'] == 'true';
  final messageId = message.messageId ?? '';

  debugPrint(
    '📦 FCM data: title=$title, location=$location, region=$region, threatType=$threatType, state=$alarmState, msgId=$messageId',
  );

  // === FEEDBACK PUSH NOTIFICATION (background) ===
  final fcmType = data['type'] ?? 'threat';
  if (fcmType == 'feedback_reply' || fcmType == 'feedback_status') {
    debugPrint('📋 Feedback push received in background: $fcmType');
    try {
      final flnp = FlutterLocalNotificationsPlugin();
      const androidInit = AndroidInitializationSettings('@mipmap/ic_launcher');
      const iosInit = DarwinInitializationSettings();
      await flnp.initialize(
        const InitializationSettings(android: androidInit, iOS: iosInit),
      );

      final androidDetails = AndroidNotificationDetails(
        'feedback_alerts',
        'Зворотний зв\'язок',
        channelDescription: 'Відповіді на ваші звернення',
        importance: Importance.high,
        priority: Priority.high,
        icon: '@mipmap/ic_launcher',
        color: const Color(0xFF5B7FFF),
        playSound: true,
        enableVibration: prefs.getBool('vibration_enabled') ?? true,
      );
      const iosDetails = DarwinNotificationDetails(
        presentAlert: true,
        presentBadge: true,
        presentSound: true,
        threadIdentifier: 'feedback',
        interruptionLevel: InterruptionLevel.active,
      );

      await flnp.show(
        _generateNotificationId(),
        title,
        body,
        NotificationDetails(android: androidDetails, iOS: iosDetails),
      );
      await _NotificationMetrics.trackShown(prefs);
    } catch (e) {
      debugPrint('Feedback notification error: $e');
    }
    return; // Skip all threat/alarm logic
  }
  // === END FEEDBACK PUSH ===

  // Отримуємо поточний час для дедуплікації та ballistic alerts
  final currentTime = DateTime.now().millisecondsSinceEpoch;

  // === BALLISTIC THREAT DETECTION (background) ===
  final lowerBody = body.toLowerCase();
  final lowerThreat = threatType.toLowerCase();

  final isBallisticThreat =
      lowerBody.contains('балістик') ||
      lowerBody.contains('балистик') ||
      lowerThreat.contains('ballistic') ||
      lowerThreat.contains('балістик');

  final isBallisticAllClear =
      (lowerBody.contains('відбій') && lowerBody.contains('балістик')) ||
      (alarmState == 'ended' && isBallisticThreat);

  // Зберігаємо для показу при відкритті додатку
  if (isBallisticAllClear) {
    debugPrint('✅ BALLISTIC ALL CLEAR detected in background for: $region');
    await prefs.setString('pending_ballistic_alert', 'all_clear');
    await prefs.setString('pending_ballistic_region', region);
    await prefs.setInt('pending_ballistic_time', currentTime);
  } else if (isBallisticThreat) {
    debugPrint('🚀 BALLISTIC THREAT detected in background for: $region');
    await prefs.setString('pending_ballistic_alert', 'threat');
    await prefs.setString('pending_ballistic_region', region);
    await prefs.setInt('pending_ballistic_time', currentTime);
  }
  // === END BALLISTIC DETECTION ===

  // === REGION FILTER (v2.1) ===
  // Перевіряємо чи FCM містить region IDs
  final oblastId = data['oblast_id'] as String?;
  final raionId = data['raion_id'] as String?;
  final settlementId = data['settlement_id'] as String?;

  debugPrint(
    '🔍 FCM region IDs: oblast=$oblastId, raion=$raionId, settlement=$settlementId',
  );

  final userSelection = await _loadUserRegionSelection(prefs);

  // If we have ID-based data, use precise filtering
  if (oblastId != null && oblastId.isNotEmpty) {
    final event = NotificationEvent.fromFcmData(data);
    final filterService = NotificationFilterService();

    if (!filterService.shouldShowNotification(event, userSelection)) {
      debugPrint(
        '🚫 ID-based filter: event oblast=$oblastId raion=$raionId NOT in user selection',
      );
      return;
    }
    debugPrint('✅ ID-based filter passed for oblast=$oblastId raion=$raionId');
  } else {
    // Fallback to legacy name-based filtering when oblast_id is missing
    debugPrint('⚠️ No oblast_id in FCM, using legacy name-based filter');
    final selectedRegions = prefs.getStringList('selected_regions') ?? [];
    final selectedRaionIds = prefs.getStringList('selected_raion_ids') ?? [];

    if (selectedRegions.isNotEmpty || selectedRaionIds.isNotEmpty) {
      // Слобожанське → Чугуївський р-н (НЕ Ізюмський!). Strict match для цих місць.
      const placeToRaion = {'Слобожанське': 'Чугуївський район'};
      final placeRaion = placeToRaion[location.trim()] ?? placeToRaion[region.trim()];
      if (placeRaion != null) {
        // Показувати тільки якщо обрано саме цей район
        final hasRaion = selectedRegions.contains(placeRaion) ||
            (selectedRaionIds.contains('UA-63-04') && placeRaion == 'Чугуївський район');
        if (!hasRaion) {
          debugPrint('🚫 Слобожанське в Чугуївському р-ні — не в обраному Ізюмському');
          return;
        }
      }

      bool regionMatch = false;
      for (final selectedRegion in selectedRegions) {
        final normalizedSelected = selectedRegion.toLowerCase().trim();
        final normalizedRegion = region.toLowerCase().trim();
        final normalizedLocation = location.toLowerCase().trim();

        if (normalizedRegion.contains(normalizedSelected) ||
            normalizedSelected.contains(normalizedRegion) ||
            normalizedLocation.contains(normalizedSelected)) {
          regionMatch = true;
          break;
        }
      }

      if (!regionMatch) {
        debugPrint('🚫 Legacy filter: region "$region" not in user selection');
        return;
      }
      debugPrint('✅ Legacy filter passed for region: $region');
    }
  }
  // === END REGION FILTER ===

  // === SLEEP MODE CHECK ===
  // Перевіряємо режим сну (статичний метод для background)
  final shouldBlockSleep = await SleepModeService.shouldBlockNotificationStatic(
    body,
  );
  if (shouldBlockSleep) {
    debugPrint('🌙 Sleep mode active - blocking notification');
    return;
  }
  // === END SLEEP MODE ===

  // Detect alarm-type FCM (air raid alert from alarm_monitor)
  final isAlarmFcm = fcmType == 'alarm';

  // === THREAT TYPE FILTER ===
  final threatKey = _resolveThreatKey(body, threatType);
  // Skip threat-type filter for alarm FCMs (alarms always go through)
  if (!isAlarmFcm && !_isThreatTypeAllowed(prefs, threatKey)) {
    debugPrint('🔕 Threat type $threatKey disabled by user settings');
    await _NotificationMetrics.trackSkipped(prefs);
    return;
  }
  // === END THREAT TYPE FILTER ===

  final criticalByType =
      isCritical ||
      isAlarmFcm ||
      threatKey == 'rocket' ||
      threatKey == 'ballistic' ||
      threatKey == 'kab';
  final allowByQuietHours = await _shouldAllowByQuietHours(
    prefs,
    isCritical: criticalByType,
  );
  if (!allowByQuietHours) {
    debugPrint('🌙 Quiet hours active - skipping notification');
    await _NotificationMetrics.trackSkipped(prefs);
    return;
  }

  // === DEDUPLICATION (using SharedPreferences for background isolate) ===
  // Use consistent key format without platform prefix to sync foreground/background
  final messageKey = messageId.isNotEmpty
      ? messageId
      : '$region|$location|$threatType|$alarmState';
  final notificationKey = 'notif|$messageKey';
  final shouldSkip = await _DedupStore.shouldSkipNotification(
    prefs,
    notificationKey,
    ttlMs: 30000,
  );
  if (shouldSkip) {
    debugPrint('🔇 Skipping duplicate notification (same message within 30s)');
    await _NotificationMetrics.trackSkipped(prefs);
    return;
  }
  // === END DEDUPLICATION ===

  // Show local notification
  try {
    final flutterLocalNotificationsPlugin = FlutterLocalNotificationsPlugin();

    // Initialize (required in background isolate)
    const androidSettings = AndroidInitializationSettings(
      '@mipmap/ic_launcher',
    );
    const iosSettings = DarwinInitializationSettings();
    const initSettings = InitializationSettings(
      android: androidSettings,
      iOS: iosSettings,
    );
    await flutterLocalNotificationsPlugin.initialize(initSettings);

    // Перевіряємо налаштування вібрації окремо
    final vibrationEnabled = prefs.getBool('vibration_enabled') ?? true;
    final shouldVibrate = vibrationEnabled;

    // Determine notification styling based on threat type
    final bool isAllClear =
        alarmState == 'ended' || body.toLowerCase().contains('відбій');
    final bool isRocket =
        threatType.toLowerCase().contains('ракет') ||
        body.toLowerCase().contains('ракет');
    final bool isDrone =
        threatType.toLowerCase().contains('бпла') ||
        body.toLowerCase().contains('бпла') ||
        threatType.toLowerCase().contains('дрон') ||
        body.toLowerCase().contains('дрон') ||
        threatType.toLowerCase().contains('шахед') ||
        body.toLowerCase().contains('шахед');
    final bool isKab =
        threatType.toLowerCase().contains('каб') ||
        body.toLowerCase().contains('каб');

    // Choose emoji and color
    String emoji;
    Color notificationColor;
    String channelId;
    String channelName;

    // Використовуємо різні канали для режимів з/без вібрації
    // Це потрібно бо Android кешує налаштування каналу при створенні
    final vibSuffix = shouldVibrate ? '' : '_silent';

    // PRO: custom alarm sound (different channel per sound on Android 8+)
    final alarmSoundId = prefs.getString(PrefsKeys.alarmSoundId) ?? 'default';
    final useCustomSound = Platform.isAndroid &&
        ProGate.isUnlocked(ProFeature.customAlarmSounds) &&
        (alarmSoundId == 'sharp' || alarmSoundId == 'siren');
    final soundSuffix = useCustomSound ? '_$alarmSoundId' : '';

    if (isAllClear) {
      emoji = '✅';
      notificationColor = const Color(0xFF30D158);
      channelId = 'all_clear_alerts$vibSuffix$soundSuffix';
      channelName = shouldVibrate
          ? 'Відбій тривоги'
          : 'Відбій тривоги (без вібро)';
    } else if (isRocket) {
      emoji = '🚀';
      notificationColor = const Color(0xFFE63946);
      channelId = 'critical_alerts$vibSuffix$soundSuffix';
      channelName = shouldVibrate
          ? 'Критичні тривоги'
          : 'Критичні тривоги (без вібро)';
    } else if (isKab) {
      emoji = '💣';
      notificationColor = const Color(0xFFE63946);
      channelId = 'critical_alerts$vibSuffix$soundSuffix';
      channelName = shouldVibrate
          ? 'Критичні тривоги'
          : 'Критичні тривоги (без вібро)';
    } else if (isDrone) {
      emoji = '🛩️';
      notificationColor = const Color(0xFFFF9500);
      channelId = 'normal_alerts$vibSuffix$soundSuffix';
      channelName = shouldVibrate
          ? 'Звичайні тривоги'
          : 'Звичайні тривоги (без вібро)';
    } else {
      emoji = '🚨';
      notificationColor = const Color(0xFFFF9500);
      channelId = 'normal_alerts$vibSuffix$soundSuffix';
      channelName = shouldVibrate
          ? 'Звичайні тривоги'
          : 'Звичайні тривоги (без вібро)';
    }

    // Format title with emoji if not already present
    final formattedTitle = title.contains(emoji) ? title : '$emoji $title';

    // Create subtext from region
    final subText = region.isNotEmpty && !body.contains(region) ? region : null;

    // BigTextStyle for better display
    final bigTextStyle = BigTextStyleInformation(
      body,
      contentTitle: formattedTitle,
      summaryText: subText,
    );

    AndroidNotificationSound? notificationSound;
    if (useCustomSound && alarmSoundId != 'default') {
      notificationSound = RawResourceAndroidNotificationSound('alarm_$alarmSoundId');
    }

    final androidDetails = AndroidNotificationDetails(
      channelId,
      channelName,
      channelDescription: 'Сповіщення про тривоги',
      importance: isCritical ? Importance.max : Importance.high,
      priority: isCritical ? Priority.max : Priority.high,
      color: notificationColor,
      colorized: true,
      playSound: true,
      sound: notificationSound,
      enableVibration: shouldVibrate,
      silent: false,
      styleInformation: bigTextStyle,
      subText: subText,
      ticker: formattedTitle,
      category: isCritical
          ? AndroidNotificationCategory.alarm
          : AndroidNotificationCategory.message,
      visibility: NotificationVisibility.public,
    );

    final iosDetails = DarwinNotificationDetails(
      presentAlert: true,
      presentBadge: true,
      presentSound: true,
      subtitle: subText,
      threadIdentifier: region.isNotEmpty ? region : 'alerts',
      interruptionLevel: isCritical
          ? InterruptionLevel.timeSensitive
          : InterruptionLevel.active,
    );

    final details = NotificationDetails(
      android: androidDetails,
      iOS: iosDetails,
    );

    try {
      await flutterLocalNotificationsPlugin.show(
        _generateNotificationId(),
        formattedTitle,
        body,
        details,
      );
    } catch (e) {
      // Fallback: custom sound resource might not exist (alarm_sharp.ogg, alarm_siren.ogg)
      if (useCustomSound) {
        debugPrint('📱 Custom sound failed, retrying with default: $e');
        final fallbackDetails = NotificationDetails(
          android: AndroidNotificationDetails(
            channelId.replaceAll('_$alarmSoundId', ''),
            channelName,
            channelDescription: 'Сповіщення про тривоги',
            importance: isCritical ? Importance.max : Importance.high,
            priority: isCritical ? Priority.max : Priority.high,
            color: notificationColor,
            colorized: true,
            playSound: true,
            enableVibration: shouldVibrate,
            silent: false,
            styleInformation: bigTextStyle,
            subText: subText,
            ticker: formattedTitle,
            category: isCritical
                ? AndroidNotificationCategory.alarm
                : AndroidNotificationCategory.message,
            visibility: NotificationVisibility.public,
          ),
          iOS: iosDetails,
        );
        await flutterLocalNotificationsPlugin.show(
          _generateNotificationId(),
          formattedTitle,
          body,
          fallbackDetails,
        );
      } else {
        rethrow;
      }
    }
    await _NotificationMetrics.trackShown(prefs);
    debugPrint('📱 Local notification shown (vibration: $vibrationEnabled)');

    // Оновлюємо віджет при FCM у фоні/закритому додатку — інакше віджет показує застарілий стан
    try {
      final isAlarm =
          alarmState != 'ended' && !body.toLowerCase().contains('відбій');
      await WidgetService().updateAlarmStatus(
        isAlarm: isAlarm,
        region: region.isNotEmpty ? region : null,
      );
    } catch (we) {
      debugPrint('Widget update in background: $we');
    }
  } catch (e) {
    debugPrint('Local notification error: $e');
  }

  // TTS in background (Android and iOS)
  try {
    final ttsEnabled = prefs.getBool('tts_enabled') ?? false;

    debugPrint(
      '🔊 TTS enabled: $ttsEnabled, Notifications: $notificationsEnabled, Platform: ${Platform.isAndroid ? "Android" : "iOS"}',
    );

    // Озвучуємо тільки якщо TTS увімкнено і сповіщення увімкнені
    if (ttsEnabled && notificationsEnabled) {
      // === TTS DEDUPLICATION ===
      // Перевіряємо чи це повідомлення вже озвучувалось
      // Use consistent key format without platform prefix to sync with foreground
      final ttsKey = '$region|$location|$threatType|$alarmState'.toLowerCase();
      final shouldSkip = await _DedupStore.shouldSkipTts(
        prefs,
        ttsKey,
        ttlMs: 60000,
      );
      if (shouldSkip) {
        debugPrint('🔇 Skipping duplicate TTS (same message within 60s)');
      } else {
        // === END TTS DEDUPLICATION ===

        final tts = FlutterTts();

        // Platform-specific TTS configuration FIRST (before language/voice)
        if (Platform.isAndroid) {
          await tts.setQueueMode(1); // QUEUE_ADD
        } else if (Platform.isIOS) {
          // iOS: configure audio session for background playback BEFORE speaking
          await tts.setSharedInstance(true);
          await tts.setIosAudioCategory(IosTextToSpeechAudioCategory.playback, [
            IosTextToSpeechAudioCategoryOptions.allowBluetooth,
            IosTextToSpeechAudioCategoryOptions.allowBluetoothA2DP,
            IosTextToSpeechAudioCategoryOptions.mixWithOthers,
            IosTextToSpeechAudioCategoryOptions.duckOthers,
          ]);
        }

        // Load volume setting from preferences
        final ttsVolume = prefs.getDouble('tts_volume') ?? 1.0;
        final ttsSpeechRate = prefs.getDouble('tts_speech_rate') ?? 0.45;
        final ttsPitch = prefs.getDouble('tts_pitch') ?? 0.9;

        // Configure TTS for background operation
        await tts.setLanguage('uk-UA');
        await tts.setSpeechRate(ttsSpeechRate);
        await tts.setVolume(ttsVolume);
        await tts.setPitch(ttsPitch);

        // Вибрати конкретний голос (жіночий українській якщо доступний)
        try {
          final voices = await tts.getVoices;
          if (voices != null) {
            // Шукаємо український голос
            final ukVoices = (voices as List).where((v) {
              final locale = (v['locale'] ?? '').toString().toLowerCase();
              return locale.contains('uk') || locale.contains('ukr');
            }).toList();

            if (ukVoices.isNotEmpty) {
              // Вибираємо перший український голос
              final voice = ukVoices.first;
              await tts.setVoice({
                'name': voice['name'],
                'locale': voice['locale'],
              });
              debugPrint('🔊 Selected voice: ${voice['name']}');
            }
          }
        } catch (e) {
          debugPrint('🔊 Voice selection error: $e');
        }

        await tts.awaitSpeakCompletion(true);

        // Використовуємо уніфіковану функцію форматування
        final speechMessage = _formatTtsMessage(
          region: region,
          location: location,
          threatType: threatType,
          alarmState: alarmState,
          body: body,
        );

        debugPrint('🔊 Background TTS: $speechMessage');

        // Speak and wait for completion
        final result = await tts.speak(speechMessage);
        if (kDebugMode) debugPrint('🔊 TTS speak result: $result');

        // Wait for speech to complete
        await Future.delayed(const Duration(seconds: 6));

        // Cleanup TTS instance
        await tts.stop();
      }
    }
  } catch (e) {
    debugPrint('Background TTS error: $e');
  }
}

class NotificationService {
  static final NotificationService _instance = NotificationService._internal();
  factory NotificationService() => _instance;
  NotificationService._internal();

  final FlutterLocalNotificationsPlugin flutterLocalNotificationsPlugin =
      FlutterLocalNotificationsPlugin();

  // Кеш для дедуплікації foreground сповіщень
  final Map<String, DateTime> _foregroundNotificationCache = {};
  static const Duration _foregroundCacheDuration = Duration(seconds: 30);

  // Lazy initialization - works on both platforms
  FirebaseMessaging? _firebaseMessaging;
  FirebaseMessaging? get firebaseMessaging {
    try {
      _firebaseMessaging ??= FirebaseMessaging.instance;
    } catch (e) {
      debugPrint('Firebase Messaging not available: $e');
    }
    return _firebaseMessaging;
  }

  bool get isFirebaseAvailable => _firebaseMessaging != null;

  /// Cached APNS readiness flag — once true stays true for session
  bool _apnsReady = false;

  /// Tracks if we have pending topic subscriptions due to APNS not being ready
  bool _hasPendingSubscriptions = false;

  /// Timer for retrying FCM token fetch
  Timer? _apnsRetryTimer;

  /// Schedule a background retry to obtain FCM token and subscribe to topics.
  /// On iOS, APNS token must be available before FCM getToken / subscribeToTopic.
  /// This timer polls getAPNSToken() and acts when it becomes available.
  void _scheduleDeferredApnsRetry() {
    if (_apnsRetryTimer?.isActive ?? false) return;
    _hasPendingSubscriptions = true;
    int retryCount = 0;
    _apnsRetryTimer = Timer.periodic(const Duration(seconds: 5), (timer) async {
      retryCount++;
      // Already have everything we need
      if (_fcmToken != null && _apnsReady) {
        timer.cancel();
        return;
      }
      final m = firebaseMessaging;
      if (m == null) {
        timer.cancel();
        return;
      }
      // Give up after 5 minutes (60 retries × 5s)
      if (retryCount > 60) {
        timer.cancel();
        debugPrint('🍎❌ APNS/FCM never obtained after 5 minutes — giving up');
        return;
      }
      try {
        // Step 1: Check if APNS token arrived
        if (!_apnsReady) {
          final apns = await m.getAPNSToken();
          if (apns != null) {
            _apnsReady = true;
            debugPrint('🍎✅ APNS token available (retry #$retryCount)');
          } else {
            // APNS still not ready — can't do anything yet
            if (retryCount % 6 == 0) {
              debugPrint('🍎⏳ APNS still not ready (attempt #$retryCount)');
            }
            return;
          }
        }

        // Step 2: APNS is ready — get FCM token
        if (_fcmToken == null) {
          try {
            final token = await m.getToken().timeout(
              const Duration(seconds: 10),
              onTimeout: () => null,
            );
            if (token != null) {
              _fcmToken = token;
              final prefs = await SharedPreferences.getInstance();
              await prefs.setString('fcm_token', token);
              if (kDebugMode) {
                debugPrint(
                  '🍎✅ FCM Token obtained (retry #$retryCount): ${token.substring(0, math.min(20, token.length))}...',
                );
              }
              await _registerDevice();
            } else {
              debugPrint('🍎⏳ getToken returned null (attempt #$retryCount)');
              return;
            }
          } catch (e) {
            debugPrint('🍎⚠️ getToken error (attempt #$retryCount): $e');
            return;
          }
        }

        // Step 3: Subscribe to saved topics
        await _resubscribeFromSavedTopics();
        timer.cancel();
        debugPrint('🍎✅ Deferred initialization complete');
      } catch (e) {
        debugPrint('🍎⚠️ Deferred retry error: $e');
      }
    });
  }

  /// Resubscribe to all topics saved in SharedPreferences
  Future<void> _resubscribeFromSavedTopics() async {
    if (!_hasPendingSubscriptions) return;
    try {
      final prefs = await SharedPreferences.getInstance();
      final savedTopics = prefs.getStringList('subscribed_topics') ?? [];
      if (savedTopics.isEmpty) {
        debugPrint('🍎 No saved topics to resubscribe to');
        _hasPendingSubscriptions = false;
        return;
      }
      debugPrint('🍎🔄 Resubscribing to ${savedTopics.length} saved topics...');
      for (final topic in savedTopics) {
        try {
          await firebaseMessaging?.subscribeToTopic(topic);
          debugPrint('🍎✅ Resubscribed to $topic');
        } catch (e) {
          debugPrint('🍎❌ Failed to resubscribe to $topic: $e');
        }
      }
      _subscribedTopics = savedTopics.toSet();
      _hasPendingSubscriptions = false;
      debugPrint(
        '🍎✅ Deferred resubscription complete: ${savedTopics.length} topics',
      );
    } catch (e) {
      debugPrint('🍎❌ Deferred resubscription error: $e');
    }
  }

  /// Check if APNS token is available (quick, non-blocking)
  Future<bool> _checkApnsReady() async {
    if (!Platform.isIOS) return true;
    if (_apnsReady) return true;
    try {
      final apns = await firebaseMessaging?.getAPNSToken();
      if (apns != null) {
        _apnsReady = true;
        debugPrint('🍎✅ APNS token is available');
        return true;
      }
    } catch (_) {}
    return false;
  }

  /// Safe FCM getToken — checks APNS first on iOS to avoid exception
  Future<String?> _safeGetToken() async {
    try {
      if (Platform.isIOS && !await _checkApnsReady()) {
        debugPrint(
          '🍎 APNS not ready — skipping getToken (will get via onTokenRefresh)',
        );
        return null;
      }
      return await firebaseMessaging?.getToken().timeout(
        const Duration(seconds: 15),
        onTimeout: () => null,
      );
    } catch (e) {
      debugPrint('🔑 safeGetToken error: $e');
      return null;
    }
  }

  /// Safe subscribe — checks APNS first on iOS to avoid apns-token-not-set exception
  Future<bool> _safeSubscribe(String topic) async {
    if (Platform.isIOS && !_apnsReady) {
      // Don't even try — will be retried via _resubscribeFromSavedTopics
      return false;
    }
    try {
      await firebaseMessaging?.subscribeToTopic(topic);
      debugPrint('✅ Subscribed to $topic');
      return true;
    } catch (e) {
      debugPrint('❌ Subscribe $topic error: $e');
      return false;
    }
  }

  /// Safe unsubscribe — checks APNS first on iOS
  Future<void> _safeUnsubscribe(String topic) async {
    if (Platform.isIOS && !_apnsReady) return; // Skip silently
    try {
      await firebaseMessaging?.unsubscribeFromTopic(topic);
      debugPrint('📴 Unsubscribed from $topic');
    } catch (e) {
      debugPrint('⚠️ Unsubscribe $topic error: $e');
    }
  }

  String? _fcmToken;
  String? get fcmToken => _fcmToken;

  String? _deviceId;
  String? get deviceId => _deviceId;

  // Notifications enabled state
  bool _notificationsEnabled = true;
  bool get isNotificationsEnabled => _notificationsEnabled;

  /// Перевіряє чи є pending ballistic alert (від background handler)
  /// Викликається при відкритті додатку
  Future<void> checkPendingBallisticAlert() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final pendingAlert = prefs.getString('pending_ballistic_alert');
      final pendingRegion = prefs.getString('pending_ballistic_region') ?? '';
      final pendingTime = prefs.getInt('pending_ballistic_time') ?? 0;

      // Очищаємо pending alert
      await prefs.remove('pending_ballistic_alert');
      await prefs.remove('pending_ballistic_region');
      await prefs.remove('pending_ballistic_time');

      if (pendingAlert == null) return;

      // Перевіряємо чи alert не застарів (не старше 5 хвилин)
      final now = DateTime.now().millisecondsSinceEpoch;
      if (now - pendingTime > 5 * 60 * 1000) {
        debugPrint('🚀 Pending ballistic alert is too old, skipping');
        return;
      }

      debugPrint(
        '🚀 Found pending ballistic alert: $pendingAlert for $pendingRegion',
      );

      if (pendingAlert == 'threat') {
        BallisticAlertService().triggerBallisticThreat(
          region: pendingRegion.isNotEmpty ? pendingRegion : null,
        );
      } else if (pendingAlert == 'all_clear') {
        BallisticAlertService().triggerBallisticAllClear(
          region: pendingRegion.isNotEmpty ? pendingRegion : null,
        );
      }
    } catch (e) {
      debugPrint('Error checking pending ballistic alert: $e');
    }
  }

  /// Set notifications enabled/disabled
  /// Also controls TTS - when notifications are off, TTS is also off
  Future<void> setNotificationsEnabled(bool enabled) async {
    _notificationsEnabled = enabled;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('notifications_enabled', enabled);
    debugPrint('🔔 Notifications ${enabled ? "enabled" : "disabled"}');

    // NOTE: We no longer auto-sync TTS with notifications
    // TTS has its own independent toggle in settings
    // Only turn OFF TTS when notifications are disabled (not ON when enabled)
    if (!enabled) {
      await TtsService().setEnabled(false);
      debugPrint('🔊 TTS disabled (notifications off)');
    }
    // When notifications are enabled, TTS keeps its current setting

    // Якщо вимкнули сповіщення - відписуємось від всіх топіків FCM
    if (!enabled) {
      await _unsubscribeFromAllTopics();
    } else {
      // Якщо увімкнули - підписуємось на збережені регіони
      var savedRegions = prefs.getStringList('selected_regions') ?? [];
      if (savedRegions.isEmpty) {
        final oblastIds = prefs.getStringList('selected_oblast_ids') ?? [];
        final raionIds = prefs.getStringList('selected_raion_ids') ?? [];
        if (oblastIds.isNotEmpty || raionIds.isNotEmpty) {
          final regionDb = RegionDatabase()..initialize();
          final names = <String>[];
          for (final id in oblastIds) {
            final name = regionDb.getOblastById(id)?.nameUk;
            if (name != null) names.add(name);
          }
          for (final raionId in raionIds) {
            final oblastId = regionDb.getOblastIdForRaion(raionId);
            if (oblastId != null) {
              final name = regionDb.getOblastById(oblastId)?.nameUk;
              if (name != null && !names.contains(name)) names.add(name);
            }
          }
          if (names.isNotEmpty) {
            savedRegions = names;
            await prefs.setStringList('selected_regions', names);
          }
        }
      }
      if (savedRegions.isNotEmpty) {
        await updateRegions(savedRegions);
      }
    }
  }

  /// Перевіряє чи foreground сповіщення є дублікатом
  bool _isDuplicateForegroundNotification(String key) {
    final lastTime = _foregroundNotificationCache[key];
    if (lastTime == null) return false;
    return DateTime.now().difference(lastTime) < _foregroundCacheDuration;
  }

  /// Позначає foreground сповіщення як показане
  void _markForegroundNotification(String key) {
    _foregroundNotificationCache[key] = DateTime.now();
    // Очищаємо старі записи
    final now = DateTime.now();
    _foregroundNotificationCache.removeWhere(
      (k, time) => now.difference(time) > const Duration(minutes: 2),
    );
  }

  /// Unsubscribe from all FCM topics
  Future<void> _unsubscribeFromAllTopics() async {
    final messaging = firebaseMessaging;
    if (messaging == null) return;

    // Unsubscribe from ALL possible region topics to avoid stale subscriptions
    for (final region in _allUkraineOblasts) {
      final topic = _regionToTopic(region);
      await _safeUnsubscribe(topic);
    }

    // Also unsubscribe from all_regions topic explicitly
    await _safeUnsubscribe('all_regions');

    _subscribedTopics.clear();
  }

  Future<void> initialize() async {
    // Get or create stable device ID
    final prefs = await SharedPreferences.getInstance();
    _deviceId = prefs.getString('device_id');
    if (_deviceId == null) {
      _deviceId = const Uuid().v4();
      await prefs.setString('device_id', _deviceId!);
      debugPrint('Created new device ID: $_deviceId');
    } else {
      debugPrint('Using existing device ID: $_deviceId');
    }

    // Load notifications enabled state
    _notificationsEnabled = prefs.getBool('notifications_enabled') ?? true;
    debugPrint('🔔 Notifications enabled: $_notificationsEnabled');

    // Якщо сповіщення вимкнені - не ініціалізуємо FCM
    if (!_notificationsEnabled) {
      debugPrint('🔕 Notifications disabled - skipping FCM initialization');
      // Все одно ініціалізуємо локальні сповіщення для інших цілей
    }

    // Initialize local notifications (works on both platforms)
    const AndroidInitializationSettings initializationSettingsAndroid =
        AndroidInitializationSettings('@mipmap/ic_launcher');

    const DarwinInitializationSettings initializationSettingsIOS =
        DarwinInitializationSettings(
          requestAlertPermission: true,
          requestBadgePermission: true,
          requestSoundPermission: true,
        );

    const InitializationSettings initializationSettings =
        InitializationSettings(
          android: initializationSettingsAndroid,
          iOS: initializationSettingsIOS,
        );

    await flutterLocalNotificationsPlugin.initialize(
      initializationSettings,
      onDidReceiveNotificationResponse: (NotificationResponse response) {
        debugPrint('Notification clicked: ${response.payload}');
        _navigateToMapFromNotification();
      },
    );

    // Firebase messaging - works on both platforms if configured
    // iOS needs GoogleService-Info.plist, Android needs google-services.json
    final messaging = firebaseMessaging;
    if (messaging == null) {
      debugPrint('Firebase Messaging not available on this platform');
      return;
    }

    // Request permission (required on iOS, recommended on Android 13+)
    NotificationSettings settings = await messaging.requestPermission(
      alert: true,
      badge: true,
      sound: true,
      provisional: false,
      criticalAlert: false, // Requires Apple approval, disabled for now
    );

    debugPrint(
      '🔔 Notification permission status: ${settings.authorizationStatus}',
    );
    if (settings.authorizationStatus == AuthorizationStatus.authorized) {
      debugPrint('✅ User granted notification permission');
    } else if (settings.authorizationStatus ==
        AuthorizationStatus.provisional) {
      debugPrint(
        '⚠️ User granted provisional permission (quiet notifications)',
      );
    } else {
      debugPrint('❌ User DENIED notification permission — push will NOT work!');
      debugPrint('❌ User must enable notifications in iOS Settings → Neptun');
    }

    // Create notification channels for Android
    const AndroidNotificationChannel channelCritical =
        AndroidNotificationChannel(
          'critical_alerts',
          'Критичні тривоги',
          description: 'Сповіщення про ракети та критичні загрози',
          importance: Importance.max,
          playSound: true,
          enableVibration: true,
        );

    const AndroidNotificationChannel channelNormal = AndroidNotificationChannel(
      'normal_alerts',
      'Звичайні тривоги',
      description: 'Сповіщення про дрони',
      importance: Importance.high,
      playSound: true,
    );

    const AndroidNotificationChannel channelAllClear =
        AndroidNotificationChannel(
          'all_clear_alerts',
          'Відбій тривоги',
          description: 'Сповіщення про відбій тривоги',
          importance: Importance.defaultImportance,
          playSound: true,
        );

    const AndroidNotificationChannel channelSOS = AndroidNotificationChannel(
      'sos_alerts',
      'SOS Сповіщення',
      description: 'Термінові SOS сигнали від родини',
      importance: Importance.max,
      playSound: true,
      enableVibration: true,
    );

    await flutterLocalNotificationsPlugin
        .resolvePlatformSpecificImplementation<
          AndroidFlutterLocalNotificationsPlugin
        >()
        ?.createNotificationChannel(channelCritical);

    await flutterLocalNotificationsPlugin
        .resolvePlatformSpecificImplementation<
          AndroidFlutterLocalNotificationsPlugin
        >()
        ?.createNotificationChannel(channelNormal);

    await flutterLocalNotificationsPlugin
        .resolvePlatformSpecificImplementation<
          AndroidFlutterLocalNotificationsPlugin
        >()
        ?.createNotificationChannel(channelAllClear);

    await flutterLocalNotificationsPlugin
        .resolvePlatformSpecificImplementation<
          AndroidFlutterLocalNotificationsPlugin
        >()
        ?.createNotificationChannel(channelSOS);

    // Get FCM token using safe helper (handles APNS wait on iOS)
    _fcmToken = await _safeGetToken();
    debugPrint('🔑 FCM Token: $_fcmToken');

    // Save FCM token to SharedPreferences for family SOS feature
    if (_fcmToken != null) {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('fcm_token', _fcmToken!);
      debugPrint('💾 FCM Token saved to SharedPreferences');
    } else {
      debugPrint('⚠️ FCM Token is NULL - will get it when APNS becomes ready');
      // On iOS, start deferred retry to get FCM token once APNS arrives
      if (Platform.isIOS) {
        _scheduleDeferredApnsRetry();
      }
    }

    // Listen to token refresh — also triggers resubscription on iOS
    messaging.onTokenRefresh.listen((newToken) async {
      _fcmToken = newToken;
      // Save updated token
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('fcm_token', newToken);
      if (kDebugMode) {
        debugPrint(
          '🔑 FCM Token refreshed: ${newToken.substring(0, math.min(20, newToken.length))}...',
        );
      }
      _registerDevice();
      // On iOS, token refresh means APNS is now ready
      if (Platform.isIOS) {
        final wasReady = _apnsReady;
        _apnsReady = true;
        _apnsRetryTimer?.cancel();
        debugPrint('🍎✅ APNS ready via token refresh');
        if (!wasReady) {
          // First time APNS became ready — need to subscribe to all topics
          _hasPendingSubscriptions = true;
        }
        await _resubscribeFromSavedTopics();
      }
    });

    // Handle foreground messages
    FirebaseMessaging.onMessage.listen((RemoteMessage message) async {
      // === ДЕТАЛЬНЕ ЛОГУВАННЯ ВСІХ FCM ПОВІДОМЛЕНЬ ===
      debugPrint('📩📩📩 FCM MESSAGE RECEIVED (FOREGROUND) 📩📩📩');
      debugPrint('📩 messageId: ${message.messageId}');
      debugPrint('📩 from: ${message.from}');
      debugPrint('📩 data: ${message.data}');
      debugPrint('📩 data[type]: ${message.data['type']}');
      debugPrint('📩 notification?.title: ${message.notification?.title}');
      debugPrint('📩 notification?.body: ${message.notification?.body}');
      debugPrint('📩📩📩 END FCM MESSAGE 📩📩📩');

      // Перевіряємо налаштування перед показом
      final prefs = await SharedPreferences.getInstance();
      final notificationsEnabled =
          prefs.getBool('notifications_enabled') ?? true;
      final vibrationEnabled = prefs.getBool('vibration_enabled') ?? true;

      if (!notificationsEnabled) {
        debugPrint(
          '🔕 Notifications disabled - skipping foreground notification',
        );
        return;
      }
      await _NotificationMetrics.trackReceived(prefs);

      final data = message.data;
      final region = data['region'] ?? '';
      final location = data['location'] ?? data['city'] ?? '';
      final threatType = data['threat_type'] ?? '';
      final alarmState = data['alarm_state'] ?? '';
      final rawBody = data['body'] ?? message.notification?.body ?? '';
      final fcmType = data['type'] ?? 'threat';
      final isAlarmFcm = fcmType == 'alarm';

      // === FEEDBACK PUSH NOTIFICATION (foreground) ===
      if (fcmType == 'feedback_reply' || fcmType == 'feedback_status') {
        debugPrint('📋 Feedback push received in foreground: $fcmType');
        final feedbackTitle =
            data['title'] ??
            message.notification?.title ??
            'Зворотний зв\'язок';
        final feedbackBody = data['body'] ?? message.notification?.body ?? '';

        final androidDetails = AndroidNotificationDetails(
          'feedback_alerts',
          'Зворотний зв\'язок',
          channelDescription: 'Відповіді на ваші звернення',
          importance: Importance.high,
          priority: Priority.high,
          icon: '@mipmap/ic_launcher',
          color: const Color(0xFF5B7FFF),
          playSound: true,
          enableVibration: vibrationEnabled,
        );
        const iosDetails = DarwinNotificationDetails(
          presentAlert: true,
          presentBadge: true,
          presentSound: true,
          threadIdentifier: 'feedback',
          interruptionLevel: InterruptionLevel.active,
        );

        await flutterLocalNotificationsPlugin.show(
          _generateNotificationId(),
          feedbackTitle,
          feedbackBody,
          NotificationDetails(android: androidDetails, iOS: iosDetails),
        );
        await _NotificationMetrics.trackShown(prefs);

        // Vibrate for feedback
        if (vibrationEnabled) {
          HapticFeedback.mediumImpact();
        }
        return; // Skip all threat/alarm logic
      }
      // === END FEEDBACK PUSH ===

      // Skip threat-type filter for alarm FCMs (alarms always go through)
      if (!isAlarmFcm) {
        final threatKey = _resolveThreatKey(rawBody, threatType);
        if (!_isThreatTypeAllowed(prefs, threatKey)) {
          debugPrint('🔕 Threat type $threatKey disabled by user settings');
          await _NotificationMetrics.trackSkipped(prefs);
          return;
        }
      }

      final threatKey = _resolveThreatKey(rawBody, threatType);
      final isCritical =
          data['is_critical'] == 'true' ||
          isAlarmFcm ||
          threatKey == 'rocket' ||
          threatKey == 'ballistic' ||
          threatKey == 'kab';
      final allowByQuietHours = await _shouldAllowByQuietHours(
        prefs,
        isCritical: isCritical,
      );
      if (!allowByQuietHours) {
        debugPrint('🌙 Quiet hours active - skipping notification');
        await _NotificationMetrics.trackSkipped(prefs);
        return;
      }

      // === DEDUPLICATION FOR FOREGROUND ===
      // Use consistent key format with background (notif| prefix instead of fg|)
      final notificationKey = 'notif|$region|$location|$threatType|$alarmState';
      if (_isDuplicateForegroundNotification(notificationKey)) {
        debugPrint(
          '🔇 Skipping duplicate foreground notification (same message within 30s)',
        );
        await _NotificationMetrics.trackSkipped(prefs);
        return;
      }
      final shouldSkip = await _DedupStore.shouldSkipNotification(
        prefs,
        notificationKey,
        ttlMs: 30000,
      );
      if (shouldSkip) {
        debugPrint(
          '🔇 Skipping duplicate foreground notification (SharedPrefs - already shown in background)',
        );
        await _NotificationMetrics.trackSkipped(prefs);
        return;
      }
      _markForegroundNotification(notificationKey);
      // === END DEDUPLICATION ===

      // === REGION FILTER (v2.1) ===
      final oblastId = data['oblast_id'] as String?;
      final raionId = data['raion_id'] as String?;
      final settlementId = data['settlement_id'] as String?;

      debugPrint(
        '🔍 FCM region IDs: oblast=$oblastId, raion=$raionId, settlement=$settlementId',
      );

      final userSelection = await _loadUserRegionSelection(prefs);

      // If we have ID-based data, use precise filtering
      if (oblastId != null && oblastId.isNotEmpty) {
        final event = NotificationEvent.fromFcmData(data);
        final filterService = NotificationFilterService();

        if (!filterService.shouldShowNotification(event, userSelection)) {
          debugPrint(
            '🚫 ID-based filter: event oblast=$oblastId raion=$raionId NOT in user selection',
          );
          return;
        }
        debugPrint(
          '✅ ID-based filter passed for oblast=$oblastId raion=$raionId',
        );
      } else {
        // Fallback to legacy name-based filtering when oblast_id is missing
        debugPrint('⚠️ No oblast_id in FCM, using legacy name-based filter');
        final selectedRegions = prefs.getStringList('selected_regions') ?? [];
        final selectedRaionIds = prefs.getStringList('selected_raion_ids') ?? [];

        if (selectedRegions.isNotEmpty || selectedRaionIds.isNotEmpty) {
          const placeToRaion = {'Слобожанське': 'Чугуївський район'};
          final placeRaion = placeToRaion[location.trim()] ?? placeToRaion[region.trim()];
          if (placeRaion != null) {
            final hasRaion = selectedRegions.contains(placeRaion) ||
                (selectedRaionIds.contains('UA-63-04') && placeRaion == 'Чугуївський район');
            if (!hasRaion) {
              debugPrint('🚫 Слобожанське в Чугуївському р-ні — не в обраному Ізюмському');
              return;
            }
          }

          bool regionMatch = false;
          for (final selectedRegion in selectedRegions) {
            final normalizedSelected = selectedRegion.toLowerCase().trim();
            final normalizedRegion = region.toLowerCase().trim();
            final normalizedLocation = location.toLowerCase().trim();

            if (normalizedRegion.contains(normalizedSelected) ||
                normalizedSelected.contains(normalizedRegion) ||
                normalizedLocation.contains(normalizedSelected)) {
              regionMatch = true;
              break;
            }
          }

          if (!regionMatch) {
            debugPrint(
              '🚫 Legacy filter: region "$region" not in user selection',
            );
            return;
          }
          debugPrint('✅ Legacy filter passed for region: $region');
        }
      }
      // === END REGION FILTER ===

      // For alarm FCMs: mark in AlarmTrackingService dedup cache to prevent
      // duplicate local notification when SSE alarm_update arrives shortly after
      if (isAlarmFcm && region.isNotEmpty) {
        final isAlarmStart = alarmState != 'end';
        AlarmTrackingService().markAlarmNotifiedByFcm(
          region,
          isStart: isAlarmStart,
        );
      }

      // Показуємо локальне сповіщення
      _showLocalNotification(message, vibrationEnabled: vibrationEnabled);

      // Запускаємо TTS та інші сервіси
      _triggerAlertServices(message);
    });

    // NOTE: onBackgroundMessage is registered in main() before runApp()
    // to ensure it works even when the app is terminated.

    // Handle notification taps when app is in background — open to Map
    FirebaseMessaging.onMessageOpenedApp.listen((RemoteMessage message) {
      debugPrint('Message clicked: ${message.notification?.title}');
      _navigateToMapFromNotification();
    });

    // App opened from terminated state by tapping notification
    final initialMessage = await FirebaseMessaging.instance.getInitialMessage();
    if (initialMessage != null) {
      debugPrint('App opened from notification tap: ${initialMessage.notification?.title}');
      Future.delayed(const Duration(milliseconds: 600), _navigateToMapFromNotification);
    }

    // Load saved topic subscriptions
    await _loadSavedSubscriptions();

    // === VERSION MIGRATION: Force re-subscribe on app update ===
    // This ensures old users get unsubscribed from all_regions and
    // properly subscribed to only their selected regions
    const currentSubscriptionVersion =
        3; // Increment this to force re-subscribe
    final lastSubscriptionVersion = prefs.getInt('subscription_version') ?? 0;

    if (lastSubscriptionVersion < currentSubscriptionVersion) {
      debugPrint(
        '🔄 Subscription version changed ($lastSubscriptionVersion -> $currentSubscriptionVersion), forcing re-subscribe...',
      );

      // Clear cached subscriptions to force fresh subscription
      _subscribedTopics.clear();
      await prefs.remove('subscribed_topics');

      // Unsubscribe from all region topics to avoid stale subscriptions
      await _unsubscribeFromAllTopics();

      // Save new version
      await prefs.setInt('subscription_version', currentSubscriptionVersion);
    }
    // === END VERSION MIGRATION ===

    // Subscribe to saved regions (restore subscriptions after app restart)
    // ALWAYS call updateRegions to ensure proper topic subscriptions
    // This also handles unsubscribing from all_regions for users with specific regions
    var savedRegions = prefs.getStringList('selected_regions') ?? [];

    // Якщо selected_regions порожній, але є ID — відновлюємо назви з RegionDatabase
    // (наприклад після міграції, перевстановлення, або іншого потоку вибору регіонів)
    if (savedRegions.isEmpty) {
      final oblastIds = prefs.getStringList('selected_oblast_ids') ?? [];
      final raionIds = prefs.getStringList('selected_raion_ids') ?? [];
      if (oblastIds.isNotEmpty || raionIds.isNotEmpty) {
        final regionDb = RegionDatabase()..initialize();
        final names = <String>[];
        for (final id in oblastIds) {
          final name = regionDb.getOblastById(id)?.nameUk;
          if (name != null) names.add(name);
        }
        for (final raionId in raionIds) {
          final oblastId = regionDb.getOblastIdForRaion(raionId);
          if (oblastId != null) {
            final name = regionDb.getOblastById(oblastId)?.nameUk;
            if (name != null && !names.contains(name)) names.add(name);
          }
        }
        if (names.isNotEmpty) {
          savedRegions = names;
          await prefs.setStringList('selected_regions', names);
          debugPrint('📍 Restored selected_regions from IDs: ${names.length} regions');
        }
      }
    }

    if (savedRegions.isEmpty) {
      debugPrint('📍 No regions selected — skipping FCM topic subscription');
      await _unsubscribeFromAllTopics();
    } else {
      await updateRegions(savedRegions);
    }

    // Register device with backend
    await _registerDevice();

    // Перевіряємо чи є pending ballistic alert (від background)
    // Трохи затримка щоб UI встиг завантажитись
    Future.delayed(const Duration(milliseconds: 500), () {
      checkPendingBallisticAlert();
    });
  }

  void _navigateToMapFromNotification() {
    try {
      if (sl.isRegistered<GoRouter>()) {
        sl<GoRouter>().go('/');
      }
    } catch (e) {
      debugPrint('Notification tap navigate error: $e');
    }
  }

  /// Trigger TTS and vibration for alert
  Future<void> _triggerAlertServices(RemoteMessage message) async {
    try {
      final data = message.data;

      // Детальне логування для діагностики
      debugPrint('📨 _triggerAlertServices called');
      debugPrint('📨 message.data: $data');
      debugPrint(
        '📨 message.notification?.title: ${message.notification?.title}',
      );
      debugPrint(
        '📨 message.notification?.body: ${message.notification?.body}',
      );

      // Check if this is an SOS message from family
      if (data['type'] == 'sos') {
        await _handleFamilySOS(data);
        return;
      }

      // Get body from data (data-only message) or notification
      final body = data['body'] ?? message.notification?.body ?? '';
      final region = data['region'] ?? '';
      final alarmState = data['alarm_state'] ?? '';
      final threatType = data['threat_type'] ?? '';
      final title = data['title'] ?? message.notification?.title ?? '';

      debugPrint(
        '📨 Parsed: body="$body", region="$region", threatType="$threatType", title="$title"',
      );

      // === BALLISTIC THREAT DETECTION ===
      // Перевіряємо чи це балістична загроза (в body, title або threatType)
      final lowerBody = body.toLowerCase();
      final lowerThreat = threatType.toLowerCase();
      final lowerTitle = title.toLowerCase();

      final isBallisticThreat =
          lowerBody.contains('балістик') ||
          lowerBody.contains('балистик') ||
          lowerThreat.contains('ballistic') ||
          lowerThreat.contains('балістик') ||
          lowerTitle.contains('балістик') ||
          lowerTitle.contains('балистик');

      final isBallisticAllClear =
          (lowerBody.contains('відбій') &&
              (lowerBody.contains('балістик') ||
                  lowerTitle.contains('балістик'))) ||
          (lowerTitle.contains('відбій') && lowerTitle.contains('балістик')) ||
          (alarmState == 'ended' && isBallisticThreat);

      debugPrint(
        '📨 isBallisticThreat: $isBallisticThreat, isBallisticAllClear: $isBallisticAllClear',
      );

      if (isBallisticAllClear) {
        debugPrint('✅ BALLISTIC ALL CLEAR detected for: $region');
        BallisticAlertService().triggerBallisticAllClear(
          region: region.isNotEmpty ? region : null,
        );
      } else if (isBallisticThreat) {
        debugPrint('🚀 BALLISTIC THREAT detected for: $region');
        BallisticAlertService().triggerBallisticThreat(
          region: region.isNotEmpty ? region : null,
        );
      }
      // === END BALLISTIC DETECTION ===

      // Import services lazily to avoid circular dependency
      final prefs = await SharedPreferences.getInstance();

      // === SLEEP MODE CHECK (foreground) ===
      final shouldBlockSleep =
          await SleepModeService.shouldBlockNotificationStatic(body);
      if (shouldBlockSleep) {
        debugPrint('🌙 Sleep mode (foreground): blocking notification');
        return;
      }
      // === END SLEEP MODE ===

      // Trigger TTS if enabled
      final ttsEnabled = prefs.getBool('tts_enabled') ?? false;
      debugPrint(
        '🔊 TTS check: enabled=$ttsEnabled, region=$region, alarmState=$alarmState',
      );
      if (ttsEnabled) {
        final threatType = data['threat_type'] ?? '';
        // Use 'location' field for specific place (city), fallback to body
        final location = data['location'] ?? body;
        debugPrint(
          '🔊 TTS: Speaking alert - location: $location, region: $region, threat: $threatType',
        );
        _speakAlert(region, location, threatType, alarmState, body);
      } else {
        debugPrint('🔇 TTS disabled in settings - skipping voice notification');
      }

      // Trigger vibration if enabled
      final vibrationEnabled = prefs.getBool('vibration_enabled') ?? true;
      if (vibrationEnabled) {
        _vibrateForAlert(body);
      }

      // Update home screen widget
      final isAlarm =
          alarmState != 'ended' && !body.toLowerCase().contains('відбій');
      if (Platform.isAndroid) {
        WidgetService().updateAlarmStatus(
          isAlarm: isAlarm,
          region: region.isNotEmpty ? region : null,
        );
      }
      // iOS Live Activity (Dynamic Island + Lock Screen)
      if (Platform.isIOS) {
        final lowerType = threatType.toLowerCase();
        final liveThreatType = lowerType.contains('баліст') ||
                lowerType.contains('ballistic') ||
                lowerType.contains('ракет')
            ? 'ballistic'
            : lowerType.contains('бпла') ||
                    lowerType.contains('drone') ||
                    lowerType.contains('shahed')
                ? 'drones'
                : 'air';
        if (isAlarm && region.isNotEmpty) {
          unawaited(LiveActivityService().start(
            region: region,
            threatType: liveThreatType,
          ));
        } else {
          unawaited(LiveActivityService().end());
        }
      }
    } catch (e) {
      debugPrint('Error triggering alert services: $e');
    }
  }

  /// Handle SOS message from family member
  Future<void> _handleFamilySOS(Map<String, dynamic> data) async {
    try {
      final senderName = data['sender_name'] ?? data['sender_code'] ?? 'Родина';
      final body = data['body'] ?? '$senderName потребує допомоги!';
      final locationAddress = data['location_address'] ?? '';

      debugPrint('🆘 Family SOS received from $senderName');

      // Always vibrate intensely for SOS using HapticFeedback
      for (int i = 0; i < 5; i++) {
        HapticFeedback.heavyImpact();
        await Future.delayed(const Duration(milliseconds: 300));
      }

      // Always speak SOS - this is an emergency!
      String message = 'Увага! СОС сигнал від $senderName.';
      if (locationAddress.isNotEmpty) {
        message += ' Локація: $locationAddress';
      }
      message += ' Потрібна допомога!';

      // Use TtsService for SOS (always speak, ignore isEnabled)
      await TtsService().speakDirect(message);

      // Show high-priority local notification
      await flutterLocalNotificationsPlugin.show(
        DateTime.now().millisecondsSinceEpoch ~/ 1000,
        '🆘 SOS від $senderName!',
        body,
        const NotificationDetails(
          android: AndroidNotificationDetails(
            'sos_alerts',
            'SOS Сповіщення',
            channelDescription: 'Термінові SOS сигнали від родини',
            importance: Importance.max,
            priority: Priority.max,
            playSound: true,
            enableVibration: true,
            fullScreenIntent: true,
            category: AndroidNotificationCategory.alarm,
          ),
          iOS: DarwinNotificationDetails(
            presentAlert: true,
            presentBadge: true,
            presentSound: true,
            interruptionLevel: InterruptionLevel.timeSensitive,
          ),
        ),
      );
    } catch (e) {
      debugPrint('Error handling family SOS: $e');
    }
  }

  Future<void> _speakAlert(
    String region,
    String location,
    String threatType,
    String alarmState,
    String body,
  ) async {
    try {
      final now = DateTime.now().millisecondsSinceEpoch;
      final ttsKey = '$region|$location|$threatType|$alarmState'.toLowerCase();

      // === SHARED DEDUPLICATION with background handler ===
      // Використовуємо SharedPreferences для синхронізації з background
      final prefs = await SharedPreferences.getInstance();
      // Також перевіряємо in-memory кеш для foreground
      if (ttsKey == _lastNotificationKey &&
          (now - _lastNotificationTime) < 60000) {
        debugPrint('🔇 Skipping duplicate foreground TTS (in-memory)');
        return;
      }

      // Перевіряємо SharedPreferences кеш (синхронізовано з background)
      final shouldSkip = await _DedupStore.shouldSkipTts(
        prefs,
        ttsKey,
        ttlMs: 60000,
      );
      if (shouldSkip) {
        debugPrint(
          '🔇 Skipping duplicate foreground TTS (SharedPrefs - already spoken by background)',
        );
        return;
      }

      // Оновлюємо in-memory кеш
      _lastNotificationKey = ttsKey;
      _lastNotificationTime = now;
      // === END SHARED DEDUPLICATION ===

      // Use singleton TtsService
      final ttsService = TtsService();

      // Використовуємо уніфіковану функцію форматування
      final message = _formatTtsMessage(
        region: region,
        location: location,
        threatType: threatType,
        alarmState: alarmState,
        body: body,
      );

      debugPrint('🔊 TTS foreground: $message');

      // Speak the message using speakDirect (bypasses isEnabled check since we already checked)
      await ttsService.speakDirect(message);
    } catch (e) {
      debugPrint('TTS speak error: $e');
    }
  }

  Future<void> _vibrateForAlert(String text) async {
    try {
      final lowerText = text.toLowerCase();

      if (lowerText.contains('відбій')) {
        // Light double tap for all clear
        await HapticFeedback.lightImpact();
        await Future.delayed(const Duration(milliseconds: 150));
        await HapticFeedback.lightImpact();
      } else if (lowerText.contains('ракет') ||
          lowerText.contains('балістичн')) {
        // Heavy urgent pattern for rockets
        for (int i = 0; i < 3; i++) {
          await HapticFeedback.heavyImpact();
          await Future.delayed(const Duration(milliseconds: 100));
        }
        await Future.delayed(const Duration(milliseconds: 200));
        await HapticFeedback.vibrate();
      } else if (lowerText.contains('бпла') || lowerText.contains('дрон')) {
        // Medium pattern for drones
        await HapticFeedback.mediumImpact();
        await Future.delayed(const Duration(milliseconds: 300));
        await HapticFeedback.mediumImpact();
      } else {
        // Standard alert
        await HapticFeedback.heavyImpact();
        await Future.delayed(const Duration(milliseconds: 200));
        await HapticFeedback.mediumImpact();
      }
    } catch (e) {
      debugPrint('Vibration error: $e');
    }
  }

  _NotificationContent _buildNotificationContent({
    required String rawTitle,
    required String rawBody,
    required String region,
    required String threatType,
    required String alarmState,
    required Map<String, dynamic> data,
  }) {
    final lowerBody = rawBody.toLowerCase();
    final lowerType = threatType.toLowerCase();

    final isAllClear = alarmState == 'ended' || lowerBody.contains('відбій');
    final isRocket = lowerType.contains('ракет') || lowerBody.contains('ракет');
    final isDrone =
        lowerType.contains('бпла') ||
        lowerBody.contains('бпла') ||
        lowerBody.contains('дрон') ||
        lowerType.contains('дрон') ||
        lowerBody.contains('шахед') ||
        lowerType.contains('шахед');
    final isKab = lowerType.contains('каб') || lowerBody.contains('каб');
    final isCritical =
        data['is_critical'] == 'true' ||
        data['type'] == 'rocket' ||
        isRocket ||
        isKab;

    final source = data['source']?.toString() ?? '';
    final time =
        data['time']?.toString() ?? data['timestamp']?.toString() ?? '';
    final normalizedThreat = _normalizeThreatLabel(threatType, rawBody);

    String title = rawTitle;
    if (title.trim().isEmpty) {
      title = isAllClear ? 'Відбій тривоги' : normalizedThreat;
    }

    String body = rawBody;
    if (body.trim().isEmpty) {
      if (region.isNotEmpty) {
        body = '$normalizedThreat · $region';
      } else {
        body = normalizedThreat;
      }
    }

    if (time.isNotEmpty) {
      body = '$body · $time';
    }

    String? subText;
    if (region.isNotEmpty) {
      subText = region;
    } else if (source.isNotEmpty) {
      subText = source;
    }

    if (source.isNotEmpty &&
        !body.toLowerCase().contains(source.toLowerCase())) {
      body = '$body · $source';
    }

    return _NotificationContent(
      title: title,
      body: body,
      subText: subText,
      isAllClear: isAllClear,
      isRocket: isRocket,
      isDrone: isDrone,
      isKab: isKab,
      isCritical: isCritical,
    );
  }

  String _normalizeThreatLabel(String threatType, String rawBody) {
    final lowerType = threatType.toLowerCase();
    final lowerBody = rawBody.toLowerCase();

    if (lowerType.contains('каб') || lowerBody.contains('каб')) {
      return 'КАБ';
    }
    if (lowerType.contains('ракет') || lowerBody.contains('ракет')) {
      return 'Ракети';
    }
    if (lowerType.contains('дрон') ||
        lowerType.contains('бпла') ||
        lowerBody.contains('шахед')) {
      return 'БПЛА';
    }
    if (lowerType.contains('авіа') || lowerBody.contains('авіа')) {
      return 'Авіація';
    }
    if (lowerType.contains('арт') || lowerBody.contains('арт')) {
      return 'Артилерія';
    }
    return threatType.isNotEmpty ? threatType : 'Тривога';
  }

  Future<void> _showLocalNotification(
    RemoteMessage message, {
    bool vibrationEnabled = true,
  }) async {
    final data = message.data;

    // Get title/body from data (data-only message) or notification
    final rawTitle = data['title'] ?? message.notification?.title ?? 'Тривога';
    final rawBody = data['body'] ?? message.notification?.body ?? '';
    final region = data['region'] ?? '';
    final threatType = data['threat_type'] ?? '';
    final alarmState = data['alarm_state'] ?? '';
    final content = _buildNotificationContent(
      rawTitle: rawTitle,
      rawBody: rawBody,
      region: region,
      threatType: threatType,
      alarmState: alarmState,
      data: data,
    );

    // Choose emoji and color based on threat type
    String emoji;
    Color notificationColor;
    String channelId;
    String channelName;

    // Використовуємо різні канали для режимів з/без вібрації
    final vibSuffix = vibrationEnabled ? '' : '_silent';

    if (content.isAllClear) {
      emoji = '✅';
      notificationColor = const Color(0xFF30D158); // Green
      channelId = 'all_clear_alerts$vibSuffix';
      channelName = vibrationEnabled
          ? 'Відбій тривоги'
          : 'Відбій тривоги (без вібро)';
    } else if (content.isRocket) {
      emoji = '🚀';
      notificationColor = const Color(0xFFE63946); // Red
      channelId = 'critical_alerts$vibSuffix';
      channelName = vibrationEnabled
          ? 'Критичні тривоги'
          : 'Критичні тривоги (без вібро)';
    } else if (content.isKab) {
      emoji = '💣';
      notificationColor = const Color(0xFFE63946); // Red
      channelId = 'critical_alerts$vibSuffix';
      channelName = vibrationEnabled
          ? 'Критичні тривоги'
          : 'Критичні тривоги (без вібро)';
    } else if (content.isDrone) {
      emoji = '🛩️';
      notificationColor = const Color(0xFFFF9500); // Orange
      channelId = 'normal_alerts$vibSuffix';
      channelName = vibrationEnabled
          ? 'Звичайні тривоги'
          : 'Звичайні тривоги (без вібро)';
    } else {
      emoji = '🚨';
      notificationColor = const Color(0xFFFF9500); // Orange
      channelId = 'normal_alerts$vibSuffix';
      channelName = vibrationEnabled
          ? 'Звичайні тривоги'
          : 'Звичайні тривоги (без вібро)';
    }

    // Format title with emoji
    final title = content.title.startsWith(emoji)
        ? content.title
        : '$emoji ${content.title}';

    // Format body - clean and informative
    String body = content.body;
    String? subText = content.subText;

    // Визначаємо налаштування вібрації
    final shouldVibrate = vibrationEnabled;

    // Create BigTextStyle for better display of long messages
    final bigTextStyle = BigTextStyleInformation(
      body,
      contentTitle: title,
      summaryText: subText,
      htmlFormatContent: false,
      htmlFormatContentTitle: false,
    );

    final androidDetails = AndroidNotificationDetails(
      channelId,
      channelName,
      channelDescription: content.isCritical
          ? 'Сповіщення про ракети та критичні загрози'
          : 'Сповіщення про повітряну тривогу',
      importance: content.isCritical ? Importance.max : Importance.high,
      priority: content.isCritical ? Priority.max : Priority.high,
      icon: '@mipmap/ic_launcher',
      color: notificationColor,
      colorized: true, // Use color for notification background
      playSound: true,
      enableVibration: shouldVibrate,
      silent: false,
      styleInformation: bigTextStyle,
      subText: subText,
      ticker: title, // Text shown in status bar
      category: content.isCritical
          ? AndroidNotificationCategory.alarm
          : AndroidNotificationCategory.message,
      visibility: NotificationVisibility.public, // Show on lock screen
    );

    final iosDetails = DarwinNotificationDetails(
      presentAlert: true,
      presentBadge: true,
      presentSound: true,
      subtitle: subText,
      threadIdentifier: region.isNotEmpty
          ? region
          : 'alerts', // Group by region
      interruptionLevel: content.isCritical
          ? InterruptionLevel.timeSensitive
          : InterruptionLevel.active,
    );

    final details = NotificationDetails(
      android: androidDetails,
      iOS: iosDetails,
    );

    await flutterLocalNotificationsPlugin.show(
      _generateNotificationId(),
      title,
      body,
      details,
      payload: jsonEncode(data),
    );
    try {
      final prefs = await SharedPreferences.getInstance();
      await _NotificationMetrics.trackShown(prefs);
    } catch (_) {}
    debugPrint('📱 Foreground notification (vibration: $vibrationEnabled)');
  }

  static const int _registerRetries = 3;
  static const Duration _registerTimeout = Duration(seconds: 15);
  static const Duration _deferredRetryDelay = Duration(minutes: 5);
  static DateTime? _lastRegisterSuccessAt;
  Timer? _deferredRegisterTimer;

  /// Call when app resumes from background — re-registers to refresh token (rate-limited to once per 30min).
  Future<void> reRegisterOnResume() async {
    if (_lastRegisterSuccessAt != null &&
        DateTime.now().difference(_lastRegisterSuccessAt!) < const Duration(minutes: 30)) {
      return; // Already registered recently
    }
    await _registerDevice();
  }

  Future<void> _registerDevice() async {
    if (_fcmToken == null || _deviceId == null) return;

    final prefs = await SharedPreferences.getInstance();
    final selectedRegions = prefs.getStringList('selected_regions') ?? [];
    final selectedOblastIds = prefs.getStringList('selected_oblast_ids') ?? [];
    final selectedRaionIds = prefs.getStringList('selected_raion_ids') ?? [];
    final notificationsEnabled = prefs.getBool('notifications_enabled') ?? true;

    if (!notificationsEnabled || selectedRegions.isEmpty) {
      debugPrint('Notifications disabled or no regions selected');
      return;
    }

    final platform = Platform.isIOS
        ? 'ios'
        : (Platform.isAndroid ? 'android' : 'other');
    if (kDebugMode) {
      debugPrint(
        '📱 Registering device: platform=$platform, token=${_fcmToken!.substring(0, math.min(30, _fcmToken!.length))}...',
      );
    }

    final payload = {
      'token': _fcmToken,
      'regions': selectedRegions,
      'oblast_ids': selectedOblastIds,
      'raion_ids': selectedRaionIds,
      'device_id': _deviceId,
      'platform': platform,
    };

    var lastError = '';
    for (var attempt = 1; attempt <= _registerRetries; attempt++) {
      try {
        final response = await http
            .post(
              Uri.parse(ApiConfig.register),
              headers: {'Content-Type': 'application/json'},
              body: jsonEncode(payload),
            )
            .timeout(_registerTimeout);

        if (response.statusCode == 200) {
          _lastRegisterSuccessAt = DateTime.now();
          _deferredRegisterTimer?.cancel();
          _deferredRegisterTimer = null;
          debugPrint(
            '✅ Device registered successfully with ID: $_deviceId, platform: $platform',
          );
          return;
        }
        lastError = 'HTTP ${response.statusCode}';
      } catch (e) {
        lastError = e.toString();
      }
      if (attempt < _registerRetries) {
        final delay = Duration(seconds: 2 * attempt);
        debugPrint('⏳ Register attempt $attempt failed ($lastError), retry in ${delay.inSeconds}s');
        await Future.delayed(delay);
      }
    }

    debugPrint('❌ Device registration failed after $_registerRetries attempts: $lastError');
    _scheduleDeferredRetry();
  }

  void _scheduleDeferredRetry() {
    _deferredRegisterTimer?.cancel();
    _deferredRegisterTimer = Timer(_deferredRetryDelay, () {
      _deferredRegisterTimer = null;
      _registerDevice();
    });
    debugPrint('⏳ Scheduled retry in ${_deferredRetryDelay.inMinutes} min');
  }

  Future<void> _unregisterDevice() async {
    if (_deviceId == null) return;

    try {
      // Send empty regions to effectively disable notifications
      final response = await http.post(
        Uri.parse(ApiConfig.register),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'token': _fcmToken ?? '',
          'regions': [], // Empty regions = no notifications
          'oblast_ids': [],
          'raion_ids': [],
          'device_id': _deviceId,
          'enabled': false,
        }),
      );

      if (response.statusCode == 200) {
        debugPrint('Device unregistered successfully');
      } else {
        debugPrint('Failed to unregister device: ${response.statusCode}');
      }
    } catch (e) {
      debugPrint('Error unregistering device: $e');
    }
  }

  Future<void> sendTestNotification() async {
    // First show local test notification immediately
    await _showTestLocalNotification();

    // Then try to send via backend (if Firebase is configured)
    if (_fcmToken == null) {
      debugPrint('No FCM token available');
      return;
    }

    try {
      final response = await http.post(
        Uri.parse(ApiConfig.testNotification),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'token': _fcmToken}),
      );

      if (response.statusCode == 200) {
        debugPrint('Test notification sent to backend');
      } else {
        debugPrint('Backend test notification failed: ${response.statusCode}');
      }
    } catch (e) {
      debugPrint('Error sending test notification to backend: $e');
    }
  }

  Future<void> _showTestLocalNotification() async {
    const androidDetails = AndroidNotificationDetails(
      'normal_alerts',
      'Звичайні тривоги',
      channelDescription: 'Сповіщення про дрони',
      importance: Importance.high,
      priority: Priority.high,
      icon: '@mipmap/ic_launcher',
      color: Color(0xFF4A90E2),
    );

    const iosDetails = DarwinNotificationDetails(
      presentAlert: true,
      presentBadge: true,
      presentSound: true,
    );

    const details = NotificationDetails(
      android: androidDetails,
      iOS: iosDetails,
    );

    await flutterLocalNotificationsPlugin.show(
      999, // Test notification ID
      '🧪 Тестове сповіщення',
      'Dron Alerts працює коректно! Ви отримуватимете сповіщення про загрози.',
      details,
      payload: jsonEncode({'type': 'test'}),
    );
  }

  // Track subscribed topics
  Set<String> _subscribedTopics = {};

  /// Міграція зі старого формату (назви) в новий ID-based формат
  Future<void> _migrateSelectionToIdsIfNeeded(
    SharedPreferences prefs,
    List<String> selectedRegions,
    RegionDatabase regionDb,
  ) async {
    // IMPORTANT: Always migrate to ensure consistency between UI and push filtering
    // Even if IDs already exist, user might have changed selection in UI

    debugPrint(
      '🔄 Migrating ${selectedRegions.length} regions to ID-based format',
    );

    final Set<String> oblastIds = {};
    final Set<String> raionIds = {};

    for (final name in selectedRegions) {
      // Try oblast first
      final oblastId = regionDb.getOblastIdByName(name);
      if (oblastId != null) {
        oblastIds.add(oblastId);
        debugPrint('  ✅ Oblast: $name -> $oblastId');
        continue;
      }

      // Try raion
      final raionId = regionDb.getRaionIdByName(name);
      if (raionId != null) {
        raionIds.add(raionId);
        debugPrint('  ✅ Raion: $name -> $raionId');
        continue;
      }

      debugPrint('  ⚠️ Unknown region: $name (not found in database)');
    }

    // Always save the migrated IDs (overwrite any previous values)
    await prefs.setStringList('selected_oblast_ids', oblastIds.toList());
    await prefs.setStringList('selected_raion_ids', raionIds.toList());

    debugPrint(
      '🔄 Migration complete: ${oblastIds.length} oblasts, ${raionIds.length} raions',
    );
  }

  /// Update region subscriptions for push notifications
  /// Users will only receive alerts for regions they've selected
  Future<void> updateRegions(List<String> selectedRegions) async {
    final messaging = firebaseMessaging;
    if (messaging == null) {
      debugPrint('Firebase Messaging not available - cannot update regions');
      return;
    }

    // Guard: якщо передано порожній список — перевіряємо prefs (race при init)
    if (selectedRegions.isEmpty) {
      final prefs = await SharedPreferences.getInstance();
      final saved = prefs.getStringList('selected_regions') ?? [];
      if (saved.isNotEmpty) {
        debugPrint('📍 updateRegions([]) ignored — using ${saved.length} saved regions from prefs');
        await updateRegions(saved);
        return;
      }
      // Справді порожній вибір — відписуємось
    }

    debugPrint(
      '📍 Updating region subscriptions: ${selectedRegions.length} regions',
    );

    // Always clear stale subscriptions before re-subscribing
    await _unsubscribeFromAllTopics();

    final prefs = await SharedPreferences.getInstance();
    final regionDb = RegionDatabase()..initialize();
    await _migrateSelectionToIdsIfNeeded(prefs, selectedRegions, regionDb);

    // Визначаємо на які ОБЛАСТІ треба підписатись (ID-based)
    final userOblastIds =
        prefs.getStringList('selected_oblast_ids')?.toSet() ?? <String>{};
    final legacyOblastId = prefs.getString('selected_oblast_id');
    if (legacyOblastId != null && legacyOblastId.isNotEmpty) {
      userOblastIds.add(legacyOblastId);
    }
    final userRaionIds =
        prefs.getStringList('selected_raion_ids')?.toSet() ?? <String>{};

    final Set<String> oblastIdsToSubscribe = {...userOblastIds};
    for (final raionId in userRaionIds) {
      final oblastId = regionDb.getOblastIdForRaion(raionId);
      if (oblastId != null) {
        oblastIdsToSubscribe.add(oblastId);
      }
    }

    final Set<String> oblastsToSubscribe = oblastIdsToSubscribe
        .map((id) => regionDb.getOblastById(id)?.nameUk)
        .whereType<String>()
        .toSet();

    debugPrint('📍 Oblasts to subscribe (ID-based): $oblastsToSubscribe');

    // Convert oblast names to valid topic names
    final newTopics = oblastsToSubscribe.map(_regionToTopic).toSet();

    // НЕ робимо cross-subscribe Kyiv city ↔ oblast — м. Київ ≠ Київська обл.
    // Користувач отримує сповіщення тільки за обраними регіонами.

    // Add all_regions topic if all regions selected
    const int totalRegions = 25;
    if (selectedRegions.length >= totalRegions) {
      newTopics.add('all_regions');
    }

    // Save topics BEFORE subscribing so deferred retry can resubscribe
    // if initial subscribe fails due to APNS not ready
    try {
      await prefs.setStringList('selected_regions', selectedRegions);
      await prefs.setStringList('subscribed_topics', newTopics.toList());
      BriefingService().invalidateCache();
      debugPrint(
        '💾 Saved ${newTopics.length} topics to SharedPreferences (before subscribe)',
      );
    } catch (e) {
      debugPrint('Error saving topics before subscribe: $e');
    }

    // Subscribe to all target topics
    // On iOS, if APNS not ready yet, _safeSubscribe will return false
    // and we'll schedule deferred retry
    int successCount = 0;
    for (final topic in newTopics) {
      final ok = await _safeSubscribe(topic);
      if (ok) successCount++;
    }

    // Update tracked subscriptions
    _subscribedTopics = newTopics;

    if (Platform.isIOS && successCount == 0 && newTopics.isNotEmpty) {
      debugPrint(
        '🍎⚠️ APNS not ready — 0/${newTopics.length} subscriptions succeeded, scheduling retry',
      );
      _hasPendingSubscriptions = true;
      _scheduleDeferredApnsRetry();
    } else {
      debugPrint(
        '✅ Region subscriptions: $successCount/${newTopics.length} succeeded',
      );
    }
    debugPrint('📋 Saved topics: $_subscribedTopics');

    // Also register/unregister with backend server
    if (selectedRegions.isEmpty) {
      await _unregisterDevice();
    } else {
      await _registerDevice();
    }
  }

  /// Convert region name to valid Firebase topic name
  /// Topics can only contain alphanumeric characters, underscores, and hyphens
  String _regionToTopic(String region) {
    // Map of Ukrainian region names to topic-safe names
    final regionMap = {
      'Вінницька область': 'vinnytska',
      'Волинська область': 'volynska',
      'Дніпропетровська область': 'dnipropetrovska',
      'Донецька область': 'donetska',
      'Житомирська область': 'zhytomyrska',
      'Закарпатська область': 'zakarpatska',
      'Запорізька область': 'zaporizka',
      'Івано-Франківська область': 'ivano_frankivska',
      'Київська область': 'kyivska',
      'Кіровоградська область': 'kirovohradska',
      'Луганська область': 'luhanska',
      'Львівська область': 'lvivska',
      'Миколаївська область': 'mykolaivska',
      'Одеська область': 'odeska',
      'Полтавська область': 'poltavska',
      'Рівненська область': 'rivnenska',
      'Сумська область': 'sumska',
      'Тернопільська область': 'ternopilska',
      'Харківська область': 'kharkivska',
      'Херсонська область': 'khersonska',
      'Хмельницька область': 'khmelnytska',
      'Черкаська область': 'cherkaska',
      'Чернівецька область': 'chernivetska',
      'Чернігівська область': 'chernihivska',
      'м. Київ': 'kyiv_city',
      'Київ': 'kyiv_city',
      'АР Крим': 'crimea',
      'Севастополь': 'sevastopol',
      'м. Севастополь': 'sevastopol',
    };

    // Return mapped topic name or sanitize the region name
    if (regionMap.containsKey(region)) {
      return 'region_${regionMap[region]}';
    }

    // Fallback: sanitize region name
    return 'region_${region.toLowerCase().replaceAll(RegExp(r'[^a-z0-9]'), '_')}';
  }

  /// Load saved topic subscriptions on startup
  Future<void> _loadSavedSubscriptions() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final savedTopics = prefs.getStringList('subscribed_topics') ?? [];
      _subscribedTopics = savedTopics.toSet();
      debugPrint(
        '📋 Loaded ${_subscribedTopics.length} saved topic subscriptions',
      );
    } catch (e) {
      debugPrint('Error loading saved subscriptions: $e');
    }
  }

  /// Show local notification for blackout status change
  /// [powerOn] - true if power turned on, false if turned off
  /// [city] - city name for display
  /// [group] - blackout group
  /// [nextChange] - next scheduled change (optional)
  Future<void> showBlackoutNotification({
    required bool powerOn,
    required String city,
    required String group,
    String? nextChange,
  }) async {
    try {
      // Check if blackout notifications are enabled
      final prefs = await SharedPreferences.getInstance();
      final blackoutNotificationsEnabled =
          prefs.getBool('blackout_notifications_enabled') ?? true;

      if (!blackoutNotificationsEnabled) {
        debugPrint('⚡ Blackout notifications disabled - skipping');
        return;
      }

      // Prepare notification content
      String title;
      String body;
      Color notificationColor;
      String channelId;

      if (powerOn) {
        title = '💡 Світло увімкнено';
        body = '$city, черга $group - електропостачання відновлено';
        if (nextChange != null) {
          body += '\nМожливе відключення о $nextChange';
        }
        notificationColor = const Color(0xFF22C55E); // Green
        channelId = 'blackout_alerts';
      } else {
        title = '⚡ Світло вимкнено';
        body = '$city, черга $group - відключення електроенергії';
        if (nextChange != null) {
          body += '\nСвітло з\'явиться о $nextChange';
        }
        notificationColor = const Color(0xFFDC2626); // Red
        channelId = 'blackout_alerts';
      }

      // Create notification channel for blackout alerts
      const AndroidNotificationChannel blackoutChannel =
          AndroidNotificationChannel(
            'blackout_alerts',
            'Відключення світла',
            description: 'Сповіщення про включення/відключення електроенергії',
            importance: Importance.high,
            playSound: true,
            enableVibration: true,
          );

      final androidPlugin = flutterLocalNotificationsPlugin
          .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin
          >();
      await androidPlugin?.createNotificationChannel(blackoutChannel);

      // Android notification details
      final androidDetails = AndroidNotificationDetails(
        channelId,
        'Відключення світла',
        channelDescription:
            'Сповіщення про включення/відключення електроенергії',
        importance: Importance.high,
        priority: Priority.high,
        color: notificationColor,
        colorized: true,
        playSound: true,
        enableVibration: true,
        icon: '@mipmap/ic_launcher',
        styleInformation: BigTextStyleInformation(body, contentTitle: title),
        category: AndroidNotificationCategory.status,
      );

      // iOS notification details
      final iosDetails = DarwinNotificationDetails(
        presentAlert: true,
        presentBadge: true,
        presentSound: true,
        threadIdentifier: 'blackout',
        interruptionLevel: InterruptionLevel.active,
      );

      final details = NotificationDetails(
        android: androidDetails,
        iOS: iosDetails,
      );

      await flutterLocalNotificationsPlugin.show(
        100 + DateTime.now().millisecondsSinceEpoch % 1000, // Unique ID
        title,
        body,
        details,
      );

      debugPrint('⚡ Blackout notification shown: ${powerOn ? "ON" : "OFF"}');

      // TTS for blackout notification
      final ttsEnabled = prefs.getBool('blackout_tts_enabled') ?? false;
      if (ttsEnabled) {
        await _speakBlackoutStatus(powerOn: powerOn, city: city, group: group);
      }
    } catch (e) {
      debugPrint('Error showing blackout notification: $e');
    }
  }

  /// Speak blackout status using TTS
  Future<void> _speakBlackoutStatus({
    required bool powerOn,
    required String city,
    required String group,
  }) async {
    try {
      final tts = TtsService();
      await tts.initialize();

      String message;
      if (powerOn) {
        message = 'Увага! $city, черга $group. Світло увімкнено.';
      } else {
        message = 'Увага! $city, черга $group. Світло вимкнено.';
      }

      await tts.speakDirect(message);
      debugPrint('⚡🔊 Blackout TTS: $message');
    } catch (e) {
      debugPrint('Blackout TTS error: $e');
    }
  }

  /// Show notification about emergency blackout mode
  Future<void> showEmergencyBlackoutNotification({
    required bool isEmergency,
    required String message,
    required String city,
  }) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final blackoutNotificationsEnabled =
          prefs.getBool('blackout_notifications_enabled') ?? true;

      if (!blackoutNotificationsEnabled) return;

      String title;
      Color notificationColor;

      if (isEmergency) {
        title = '🚨 Екстрені відключення';
        notificationColor = const Color(0xFFDC2626); // Red
      } else {
        title = '✅ Графіки відновлено';
        notificationColor = const Color(0xFF22C55E); // Green
      }

      final androidDetails = AndroidNotificationDetails(
        'blackout_alerts',
        'Відключення світла',
        channelDescription:
            'Сповіщення про включення/відключення електроенергії',
        importance: Importance.high,
        priority: Priority.high,
        color: notificationColor,
        colorized: true,
        playSound: true,
        enableVibration: true,
        styleInformation: BigTextStyleInformation(message, contentTitle: title),
      );

      final iosDetails = DarwinNotificationDetails(
        presentAlert: true,
        presentBadge: true,
        presentSound: true,
        threadIdentifier: 'blackout_emergency',
      );

      await flutterLocalNotificationsPlugin.show(
        200 + DateTime.now().millisecondsSinceEpoch % 1000,
        title,
        message,
        NotificationDetails(android: androidDetails, iOS: iosDetails),
      );

      debugPrint('🚨 Emergency blackout notification shown');
    } catch (e) {
      debugPrint('Error showing emergency notification: $e');
    }
  }
}
