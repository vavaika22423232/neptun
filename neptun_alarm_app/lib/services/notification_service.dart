import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:uuid/uuid.dart';
import 'tts_service.dart';
import 'ballistic_alert_service.dart';
import 'widget_service.dart';
import 'sleep_mode_service.dart';
import '../models/notification_event.dart';
import '../models/user_region_selection.dart';
import 'notification_filter_service.dart';
import 'region_database.dart';

// Track last notification to prevent duplicates (for foreground only)
String _lastNotificationKey = '';
int _lastNotificationTime = 0;

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
Future<UserRegionSelection> _loadUserRegionSelection(SharedPreferences prefs) async {
  final Set<String> oblastIds =
      (prefs.getStringList('selected_oblast_ids') ?? []).toSet();
  final legacyOblastId = prefs.getString('selected_oblast_id');
  if (legacyOblastId != null && legacyOblastId.isNotEmpty) {
    oblastIds.add(legacyOblastId);
  }

  final Set<String> raionIds =
      (prefs.getStringList('selected_raion_ids') ?? []).toSet();
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
  if (text.contains('бпла') || text.contains('дрон') || text.contains('шахед')) {
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
  
  final data = message.data;
  final title = data['title'] ?? message.notification?.title ?? 'Тривога';
  // FCM sends location in data['location'], body in notification.body
  final location = data['location'] ?? '';  // Specific place (city)
  final body = data['body'] ?? message.notification?.body ?? location;  // Fallback to location
  final region = data['region'] ?? '';  // Oblast
  final threatType = data['threat_type'] ?? '';  // Threat type (БПЛА, ракети, etc.)
  final alarmState = data['alarm_state'] ?? '';
  final isCritical = data['is_critical'] == 'true';
  final messageId = message.messageId ?? '';
  
  debugPrint('📦 FCM data: title=$title, location=$location, region=$region, threatType=$threatType, state=$alarmState, msgId=$messageId');
  
  // Отримуємо поточний час для дедуплікації та ballistic alerts
  final currentTime = DateTime.now().millisecondsSinceEpoch;
  
  // === BALLISTIC THREAT DETECTION (background) ===
  final lowerBody = body.toLowerCase();
  final lowerThreat = threatType.toLowerCase();
  
  final isBallisticThreat = lowerBody.contains('балістик') || 
                            lowerBody.contains('балистик') ||
                            lowerThreat.contains('ballistic') ||
                            lowerThreat.contains('балістик');
  
  final isBallisticAllClear = (lowerBody.contains('відбій') && lowerBody.contains('балістик')) ||
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
  
  // === ID-BASED REGION FILTER (v2.0) ===
  // Перевіряємо чи FCM містить region IDs
  final oblastId = data['oblast_id'] as String?;
  final raionId = data['raion_id'] as String?;
  final settlementId = data['settlement_id'] as String?;
  
  debugPrint('🔍 FCM region IDs: oblast=$oblastId, raion=$raionId, settlement=$settlementId');
  
  if (oblastId == null || oblastId.isEmpty) {
    debugPrint('🚫 ID-based filter: missing oblast_id in FCM payload');
    return;
  }
  
  final userSelection = await _loadUserRegionSelection(prefs);
  
  final event = NotificationEvent.fromFcmData(data);
  final filterService = NotificationFilterService();
  
  if (!filterService.shouldShowNotification(event, userSelection)) {
    debugPrint('🚫 ID-based filter: event oblast=$oblastId raion=$raionId NOT in user selection');
    return;
  }
  debugPrint('✅ ID-based filter passed for oblast=$oblastId raion=$raionId');
  // === END ID-BASED REGION FILTER ===
  
  // === SLEEP MODE CHECK ===
  // Перевіряємо режим сну (статичний метод для background)
  final shouldBlockSleep = await SleepModeService.shouldBlockNotificationStatic(body);
  if (shouldBlockSleep) {
    debugPrint('🌙 Sleep mode active - blocking notification');
    return;
  }
  // === END SLEEP MODE ===
  
  // === DEDUPLICATION (using SharedPreferences for background isolate) ===
  final notificationKey = '$region|$location|$threatType|$alarmState';
  final lastNotificationKey = prefs.getString('last_notification_key') ?? '';
  final lastNotificationTime = prefs.getInt('last_notification_time') ?? 0;
  
  if (notificationKey == lastNotificationKey && (currentTime - lastNotificationTime) < 30000) {
    debugPrint('🔇 Skipping duplicate notification (same message within 30s)');
    return;
  }
  
  // Зберігаємо для майбутньої перевірки
  await prefs.setString('last_notification_key', notificationKey);
  await prefs.setInt('last_notification_time', currentTime);
  // === END DEDUPLICATION ===
  
  // Show local notification
  try {
    final flutterLocalNotificationsPlugin = FlutterLocalNotificationsPlugin();
    
    // Initialize (required in background isolate)
    const androidSettings = AndroidInitializationSettings('@mipmap/ic_launcher');
    const iosSettings = DarwinInitializationSettings();
    const initSettings = InitializationSettings(android: androidSettings, iOS: iosSettings);
    await flutterLocalNotificationsPlugin.initialize(initSettings);
    
    // Перевіряємо налаштування вібрації окремо
    final vibrationEnabled = prefs.getBool('vibration_enabled') ?? true;
    final shouldVibrate = vibrationEnabled;
    
    // Determine notification styling based on threat type
    final bool isAllClear = alarmState == 'ended' || body.toLowerCase().contains('відбій');
    final bool isRocket = threatType.toLowerCase().contains('ракет') || body.toLowerCase().contains('ракет');
    final bool isDrone = threatType.toLowerCase().contains('бпла') || body.toLowerCase().contains('бпла');
    final bool isKab = threatType.toLowerCase().contains('каб') || body.toLowerCase().contains('каб');
    
    // Choose emoji and color
    String emoji;
    Color notificationColor;
    String channelId;
    String channelName;
    
    // Використовуємо різні канали для режимів з/без вібрації
    // Це потрібно бо Android кешує налаштування каналу при створенні
    final vibSuffix = shouldVibrate ? '' : '_silent';
    
    if (isAllClear) {
      emoji = '✅';
      notificationColor = const Color(0xFF30D158);
      channelId = 'all_clear_alerts$vibSuffix';
      channelName = shouldVibrate ? 'Відбій тривоги' : 'Відбій тривоги (без вібро)';
    } else if (isRocket) {
      emoji = '🚀';
      notificationColor = const Color(0xFFE63946);
      channelId = 'critical_alerts$vibSuffix';
      channelName = shouldVibrate ? 'Критичні тривоги' : 'Критичні тривоги (без вібро)';
    } else if (isKab) {
      emoji = '💣';
      notificationColor = const Color(0xFFE63946);
      channelId = 'critical_alerts$vibSuffix';
      channelName = shouldVibrate ? 'Критичні тривоги' : 'Критичні тривоги (без вібро)';
    } else if (isDrone) {
      emoji = '🛩️';
      notificationColor = const Color(0xFFFF9500);
      channelId = 'normal_alerts$vibSuffix';
      channelName = shouldVibrate ? 'Звичайні тривоги' : 'Звичайні тривоги (без вібро)';
    } else {
      emoji = '🚨';
      notificationColor = const Color(0xFFFF9500);
      channelId = 'normal_alerts$vibSuffix';
      channelName = shouldVibrate ? 'Звичайні тривоги' : 'Звичайні тривоги (без вібро)';
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
    
    final androidDetails = AndroidNotificationDetails(
      channelId,
      channelName,
      channelDescription: 'Сповіщення про тривоги',
      importance: isCritical ? Importance.max : Importance.high,
      priority: isCritical ? Priority.max : Priority.high,
      color: notificationColor,
      colorized: true,
      playSound: true,
      // Використовуємо системний звук - custom звуки потребують файлів в res/raw
      enableVibration: shouldVibrate,
      silent: false,
      styleInformation: bigTextStyle,
      subText: subText,
      ticker: formattedTitle,
      category: isCritical ? AndroidNotificationCategory.alarm : AndroidNotificationCategory.message,
      visibility: NotificationVisibility.public,
    );
    
    final iosDetails = DarwinNotificationDetails(
      presentAlert: true,
      presentBadge: true,
      presentSound: true,
      subtitle: subText,
      threadIdentifier: region.isNotEmpty ? region : 'alerts',
      interruptionLevel: isCritical ? InterruptionLevel.timeSensitive : InterruptionLevel.active,
    );
    
    final details = NotificationDetails(android: androidDetails, iOS: iosDetails);
    
    await flutterLocalNotificationsPlugin.show(
      DateTime.now().millisecondsSinceEpoch ~/ 1000,
      formattedTitle,
      body,
      details,
    );
    debugPrint('📱 Local notification shown (vibration: $vibrationEnabled)');
  } catch (e) {
    debugPrint('Local notification error: $e');
  }
  
  // TTS in background (Android only)
  try {
    final ttsEnabled = prefs.getBool('tts_enabled') ?? false;
    
    debugPrint('🔊 TTS enabled: $ttsEnabled, Notifications: $notificationsEnabled, Platform: ${Platform.isAndroid ? "Android" : "Other"}');
    
    // Озвучуємо тільки якщо TTS увімкнено і сповіщення увімкнені
    if (ttsEnabled && notificationsEnabled && Platform.isAndroid) {
      // === TTS DEDUPLICATION ===
      // Перевіряємо чи це повідомлення вже озвучувалось
      final ttsKey = '$region|$location|$threatType|$alarmState'.toLowerCase();
      final lastTtsKey = prefs.getString('last_tts_key') ?? '';
      final lastTtsTime = prefs.getInt('last_tts_time') ?? 0;
      
      if (ttsKey == lastTtsKey && (currentTime - lastTtsTime) < 60000) {
        debugPrint('🔇 Skipping duplicate TTS (same message within 60s)');
      } else {
        // Зберігаємо для майбутньої перевірки
        await prefs.setString('last_tts_key', ttsKey);
        await prefs.setInt('last_tts_time', currentTime);
        // === END TTS DEDUPLICATION ===
        
        final tts = FlutterTts();
        
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
              await tts.setVoice({'name': voice['name'], 'locale': voice['locale']});
              debugPrint('🔊 Selected voice: ${voice['name']}');
            }
          }
        } catch (e) {
          debugPrint('🔊 Voice selection error: $e');
        }
        
        await tts.awaitSpeakCompletion(true);
        
        // Request audio focus for background playback
        await tts.setQueueMode(1); // QUEUE_ADD
        
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
        debugPrint('🔊 TTS speak result: $result');
        
        // Wait for speech to complete
        await Future.delayed(const Duration(seconds: 6));
        debugPrint('🔊 Background TTS completed');
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
      
      debugPrint('🚀 Found pending ballistic alert: $pendingAlert for $pendingRegion');
      
      if (pendingAlert == 'threat') {
        BallisticAlertService().triggerBallisticThreat(region: pendingRegion.isNotEmpty ? pendingRegion : null);
      } else if (pendingAlert == 'all_clear') {
        BallisticAlertService().triggerBallisticAllClear(region: pendingRegion.isNotEmpty ? pendingRegion : null);
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
      final savedRegions = prefs.getStringList('selected_regions') ?? [];
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
    _foregroundNotificationCache.removeWhere((k, time) => 
      now.difference(time) > const Duration(minutes: 2));
  }
  
  /// Unsubscribe from all FCM topics
  Future<void> _unsubscribeFromAllTopics() async {
    try {
      final messaging = firebaseMessaging;
      if (messaging == null) return;

      // Unsubscribe from ALL possible region topics to avoid stale subscriptions
      for (final region in _allUkraineOblasts) {
        final topic = _regionToTopic(region);
        await messaging.unsubscribeFromTopic(topic);
        debugPrint('📴 Unsubscribed from topic: $topic');
      }

      // Also unsubscribe from all_regions topic explicitly
      await messaging.unsubscribeFromTopic('all_regions');
      debugPrint('📴 Unsubscribed from topic: all_regions');

      _subscribedTopics.clear();
    } catch (e) {
      debugPrint('Error unsubscribing from topics: $e');
    }
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
      criticalAlert: false,  // Requires Apple approval, disabled for now
    );

    if (settings.authorizationStatus == AuthorizationStatus.authorized) {
      debugPrint('User granted notification permission');
    } else if (settings.authorizationStatus == AuthorizationStatus.provisional) {
      debugPrint('User granted provisional permission');
    } else {
      debugPrint('User denied notification permission');
    }

    // Create notification channels for Android
    const AndroidNotificationChannel channelCritical = AndroidNotificationChannel(
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
    
    const AndroidNotificationChannel channelAllClear = AndroidNotificationChannel(
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
            AndroidFlutterLocalNotificationsPlugin>()
        ?.createNotificationChannel(channelCritical);

    await flutterLocalNotificationsPlugin
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>()
        ?.createNotificationChannel(channelNormal);
    
    await flutterLocalNotificationsPlugin
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>()
        ?.createNotificationChannel(channelAllClear);
    
    await flutterLocalNotificationsPlugin
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>()
        ?.createNotificationChannel(channelSOS);

    // Get FCM token
    _fcmToken = await messaging.getToken();
    debugPrint('🔑 FCM Token: $_fcmToken');
    
    // iOS-specific: Wait for APNs token before proceeding
    // Topic subscriptions on iOS require APNs token to be available
    // CRITICAL: Without APNs token, push notifications WON'T work on iOS!
    if (Platform.isIOS) {
      debugPrint('🍎 iOS: Waiting for APNs token (critical for push)...');
      String? apnsToken;
      
      // Try to get APNs token with more retries and longer delays
      // Production APNs can take longer to respond than sandbox
      for (int i = 0; i < 30; i++) {
        apnsToken = await messaging.getAPNSToken();
        if (apnsToken != null) {
          debugPrint('🍎✅ iOS APNs Token received on attempt ${i + 1}: ${apnsToken.length} characters');
          break;
        }
        debugPrint('🍎⏳ iOS APNs Token attempt ${i + 1}/30: not yet available, waiting...');
        await Future.delayed(const Duration(milliseconds: 500));
      }
      
      if (apnsToken != null) {
        debugPrint('🍎 APNs Token: $apnsToken');
        debugPrint('✅ iOS APNs token ready - topic subscriptions will work');
        // Save APNs token for diagnostics
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('apns_token', apnsToken);
      } else {
        debugPrint('🍎❌ CRITICAL: iOS APNs Token is NULL after 30 attempts!');
        debugPrint('🍎❌ Push notifications will NOT work!');
        debugPrint('🍎❌ Possible causes:');
        debugPrint('🍎❌ 1) Push Notifications capability not enabled in Xcode');
        debugPrint('🍎❌ 2) Invalid provisioning profile');
        debugPrint('🍎❌ 3) App ID not configured for push on Apple Developer Portal');
        debugPrint('🍎❌ 4) Running on simulator (APNs only works on physical devices)');
      }
    }
    
    // Save FCM token to SharedPreferences for family SOS feature
    if (_fcmToken != null) {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('fcm_token', _fcmToken!);
      debugPrint('💾 FCM Token saved to SharedPreferences');
    } else {
      debugPrint('⚠️ FCM Token is NULL - cannot receive push notifications!');
    }

    // Listen to token refresh
    messaging.onTokenRefresh.listen((newToken) async {
      _fcmToken = newToken;
      // Save updated token
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('fcm_token', newToken);
      _registerDevice();
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
      final notificationsEnabled = prefs.getBool('notifications_enabled') ?? true;
      final vibrationEnabled = prefs.getBool('vibration_enabled') ?? true;
      
      if (!notificationsEnabled) {
        debugPrint('🔕 Notifications disabled - skipping foreground notification');
        return;
      }
      
      final data = message.data;
      final region = data['region'] ?? '';
      final location = data['location'] ?? '';
      final threatType = data['threat_type'] ?? '';
      final alarmState = data['alarm_state'] ?? '';
      
      // === DEDUPLICATION FOR FOREGROUND ===
      final notificationKey = '$region|$location|$threatType|$alarmState';
      if (_isDuplicateForegroundNotification(notificationKey)) {
        debugPrint('🔇 Skipping duplicate foreground notification (same message within 30s)');
        return;
      }
      _markForegroundNotification(notificationKey);
      // === END DEDUPLICATION ===
      
      // === ID-BASED REGION FILTER (v2.0) ===
      final oblastId = data['oblast_id'] as String?;
      final raionId = data['raion_id'] as String?;
      final settlementId = data['settlement_id'] as String?;
      
      debugPrint('🔍 FCM region IDs: oblast=$oblastId, raion=$raionId, settlement=$settlementId');
      
      if (oblastId == null || oblastId.isEmpty) {
        debugPrint('🚫 ID-based filter: missing oblast_id in FCM payload');
        return;
      }
      
      final userSelection = await _loadUserRegionSelection(prefs);
      
      final event = NotificationEvent.fromFcmData(data);
      final filterService = NotificationFilterService();
      
      if (!filterService.shouldShowNotification(event, userSelection)) {
        debugPrint('🚫 ID-based filter: event oblast=$oblastId raion=$raionId NOT in user selection');
        return;
      }
      debugPrint('✅ ID-based filter passed for oblast=$oblastId raion=$raionId');
      // === END ID-BASED REGION FILTER ===
      
      // Показуємо локальне сповіщення
      _showLocalNotification(message, vibrationEnabled: vibrationEnabled);
      
      // Запускаємо TTS та інші сервіси
      _triggerAlertServices(message);
    });

    // Handle background messages
    FirebaseMessaging.onBackgroundMessage(firebaseMessagingBackgroundHandler);

    // Handle notification taps when app is in background
    FirebaseMessaging.onMessageOpenedApp.listen((RemoteMessage message) {
      debugPrint('Message clicked: ${message.notification?.title}');
    });

    // Load saved topic subscriptions
    await _loadSavedSubscriptions();

    // === VERSION MIGRATION: Force re-subscribe on app update ===
    // This ensures old users get unsubscribed from all_regions and 
    // properly subscribed to only their selected regions
    const currentSubscriptionVersion = 3; // Increment this to force re-subscribe
    final lastSubscriptionVersion = prefs.getInt('subscription_version') ?? 0;
    
    if (lastSubscriptionVersion < currentSubscriptionVersion) {
      debugPrint('🔄 Subscription version changed ($lastSubscriptionVersion -> $currentSubscriptionVersion), forcing re-subscribe...');
      
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
    
    // AUTO-SUBSCRIBE: If no regions selected (first launch), subscribe to ALL regions
    // This ensures users get notifications by default until they configure
    if (savedRegions.isEmpty) {
      debugPrint('📍 No regions selected - auto-subscribing to all regions (first launch)');
      savedRegions = _allUkraineOblasts;
      await prefs.setStringList('selected_regions', savedRegions);
      debugPrint('📍 Auto-saved ${savedRegions.length} regions');
    }
    
    await updateRegions(savedRegions);

    // Register device with backend
    await _registerDevice();
    
    // Перевіряємо чи є pending ballistic alert (від background)
    // Трохи затримка щоб UI встиг завантажитись
    Future.delayed(const Duration(milliseconds: 500), () {
      checkPendingBallisticAlert();
    });
  }

  /// Trigger TTS and vibration for alert
  Future<void> _triggerAlertServices(RemoteMessage message) async {
    try {
      final data = message.data;
      
      // Детальне логування для діагностики
      debugPrint('📨 _triggerAlertServices called');
      debugPrint('📨 message.data: $data');
      debugPrint('📨 message.notification?.title: ${message.notification?.title}');
      debugPrint('📨 message.notification?.body: ${message.notification?.body}');
      
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
      
      debugPrint('📨 Parsed: body="$body", region="$region", threatType="$threatType", title="$title"');
      
      // === BALLISTIC THREAT DETECTION ===
      // Перевіряємо чи це балістична загроза (в body, title або threatType)
      final lowerBody = body.toLowerCase();
      final lowerThreat = threatType.toLowerCase();
      final lowerTitle = title.toLowerCase();
      
      final isBallisticThreat = lowerBody.contains('балістик') || 
                                lowerBody.contains('балистик') ||
                                lowerThreat.contains('ballistic') ||
                                lowerThreat.contains('балістик') ||
                                lowerTitle.contains('балістик') ||
                                lowerTitle.contains('балистик');
      
      final isBallisticAllClear = (lowerBody.contains('відбій') && (lowerBody.contains('балістик') || lowerTitle.contains('балістик'))) ||
                                   (lowerTitle.contains('відбій') && lowerTitle.contains('балістик')) ||
                                   (alarmState == 'ended' && isBallisticThreat);
      
      debugPrint('📨 isBallisticThreat: $isBallisticThreat, isBallisticAllClear: $isBallisticAllClear');
      
      if (isBallisticAllClear) {
        debugPrint('✅ BALLISTIC ALL CLEAR detected for: $region');
        BallisticAlertService().triggerBallisticAllClear(region: region.isNotEmpty ? region : null);
      } else if (isBallisticThreat) {
        debugPrint('🚀 BALLISTIC THREAT detected for: $region');
        BallisticAlertService().triggerBallisticThreat(region: region.isNotEmpty ? region : null);
      }
      // === END BALLISTIC DETECTION ===
      
      // Import services lazily to avoid circular dependency
      final prefs = await SharedPreferences.getInstance();
      
      // === SLEEP MODE CHECK (foreground) ===
      final shouldBlockSleep = await SleepModeService.shouldBlockNotificationStatic(body);
      if (shouldBlockSleep) {
        debugPrint('🌙 Sleep mode (foreground): blocking notification');
        return;
      }
      // === END SLEEP MODE ===
      
      // Trigger TTS if enabled
      final ttsEnabled = prefs.getBool('tts_enabled') ?? false;
      debugPrint('🔊 TTS check: enabled=$ttsEnabled, region=$region, alarmState=$alarmState');
      if (ttsEnabled) {
        final threatType = data['threat_type'] ?? '';
        // Use 'location' field for specific place (city), fallback to body
        final location = data['location'] ?? body;
        debugPrint('🔊 TTS: Speaking alert - location: $location, region: $region, threat: $threatType');
        _speakAlert(region, location, threatType, alarmState);
      } else {
        debugPrint('🔇 TTS disabled in settings - skipping voice notification');
      }
      
      // Trigger vibration if enabled
      final vibrationEnabled = prefs.getBool('vibration_enabled') ?? true;
      if (vibrationEnabled) {
        _vibrateForAlert(body);
      }
      
      // Update home screen widget
      if (Platform.isAndroid) {
        final isAlarm = alarmState != 'ended' && !body.toLowerCase().contains('відбій');
        WidgetService().updateAlarmStatus(
          isAlarm: isAlarm,
          region: region.isNotEmpty ? region : null,
        );
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

  Future<void> _speakAlert(String region, String location, String threatType, String alarmState) async {
    try {
      final now = DateTime.now().millisecondsSinceEpoch;
      final ttsKey = '$region|$location|$threatType|$alarmState'.toLowerCase();
      
      // === SHARED DEDUPLICATION with background handler ===
      // Використовуємо SharedPreferences для синхронізації з background
      final prefs = await SharedPreferences.getInstance();
      final lastTtsKey = prefs.getString('last_tts_key') ?? '';
      final lastTtsTime = prefs.getInt('last_tts_time') ?? 0;
      
      // Також перевіряємо in-memory кеш для foreground
      if (ttsKey == _lastNotificationKey && (now - _lastNotificationTime) < 60000) {
        debugPrint('🔇 Skipping duplicate foreground TTS (in-memory)');
        return;
      }
      
      // Перевіряємо SharedPreferences кеш (синхронізовано з background)
      if (ttsKey == lastTtsKey && (now - lastTtsTime) < 60000) {
        debugPrint('🔇 Skipping duplicate foreground TTS (SharedPrefs - already spoken by background)');
        return;
      }
      
      // Оновлюємо обидва кеші
      _lastNotificationKey = ttsKey;
      _lastNotificationTime = now;
      await prefs.setString('last_tts_key', ttsKey);
      await prefs.setInt('last_tts_time', now);
      // === END SHARED DEDUPLICATION ===
      
      // Use singleton TtsService 
      final ttsService = TtsService();
      
      // Використовуємо уніфіковану функцію форматування
      final message = _formatTtsMessage(
        region: region,
        location: location,
        threatType: threatType,
        alarmState: alarmState,
        body: threatType, // В foreground body = threatType
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
      } else if (lowerText.contains('ракет') || lowerText.contains('балістичн')) {
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

  Future<void> _showLocalNotification(RemoteMessage message, {bool vibrationEnabled = true}) async {
    final data = message.data;
    
    // Get title/body from data (data-only message) or notification
    final rawTitle = data['title'] ?? message.notification?.title ?? 'Тривога';
    final rawBody = data['body'] ?? message.notification?.body ?? '';
    final region = data['region'] ?? '';
    final threatType = data['threat_type'] ?? '';
    final alarmState = data['alarm_state'] ?? '';
    final isCritical = data['is_critical'] == 'true' || data['type'] == 'rocket';
    
    // Determine notification type and styling
    final bool isAllClear = alarmState == 'ended' || rawBody.toLowerCase().contains('відбій');
    final bool isRocket = threatType.toLowerCase().contains('ракет') || rawBody.toLowerCase().contains('ракет');
    final bool isDrone = threatType.toLowerCase().contains('бпла') || rawBody.toLowerCase().contains('бпла') || rawBody.toLowerCase().contains('дрон');
    final bool isKab = threatType.toLowerCase().contains('каб') || rawBody.toLowerCase().contains('каб');
    
    // Choose emoji and color based on threat type
    String emoji;
    Color notificationColor;
    String channelId;
    String channelName;
    
    // Використовуємо різні канали для режимів з/без вібрації
    final vibSuffix = vibrationEnabled ? '' : '_silent';
    
    if (isAllClear) {
      emoji = '✅';
      notificationColor = const Color(0xFF30D158);  // Green
      channelId = 'all_clear_alerts$vibSuffix';
      channelName = vibrationEnabled ? 'Відбій тривоги' : 'Відбій тривоги (без вібро)';
    } else if (isRocket) {
      emoji = '🚀';
      notificationColor = const Color(0xFFE63946);  // Red
      channelId = 'critical_alerts$vibSuffix';
      channelName = vibrationEnabled ? 'Критичні тривоги' : 'Критичні тривоги (без вібро)';
    } else if (isKab) {
      emoji = '💣';
      notificationColor = const Color(0xFFE63946);  // Red
      channelId = 'critical_alerts$vibSuffix';
      channelName = vibrationEnabled ? 'Критичні тривоги' : 'Критичні тривоги (без вібро)';
    } else if (isDrone) {
      emoji = '🛩️';
      notificationColor = const Color(0xFFFF9500);  // Orange
      channelId = 'normal_alerts$vibSuffix';
      channelName = vibrationEnabled ? 'Звичайні тривоги' : 'Звичайні тривоги (без вібро)';
    } else {
      emoji = '🚨';
      notificationColor = const Color(0xFFFF9500);  // Orange
      channelId = 'normal_alerts$vibSuffix';
      channelName = vibrationEnabled ? 'Звичайні тривоги' : 'Звичайні тривоги (без вібро)';
    }
    
    // Format title with emoji
    final title = rawTitle.startsWith(emoji) ? rawTitle : '$emoji $rawTitle';
    
    // Format body - clean and informative
    String body = rawBody;
    String? subText;
    
    // Add subtext with region info if available
    if (region.isNotEmpty && !body.contains(region)) {
      subText = region;
    }

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
      channelDescription: isCritical
          ? 'Сповіщення про ракети та критичні загрози'
          : 'Сповіщення про повітряну тривогу',
      importance: isCritical ? Importance.max : Importance.high,
      priority: isCritical ? Priority.max : Priority.high,
      icon: '@mipmap/ic_launcher',
      color: notificationColor,
      colorized: true,  // Use color for notification background
      playSound: true,
      enableVibration: shouldVibrate,
      silent: false,
      styleInformation: bigTextStyle,
      subText: subText,
      ticker: title,  // Text shown in status bar
      category: isCritical ? AndroidNotificationCategory.alarm : AndroidNotificationCategory.message,
      visibility: NotificationVisibility.public,  // Show on lock screen
    );

    final iosDetails = DarwinNotificationDetails(
      presentAlert: true,
      presentBadge: true,
      presentSound: true,
      subtitle: subText,
      threadIdentifier: region.isNotEmpty ? region : 'alerts',  // Group by region
      interruptionLevel: isCritical ? InterruptionLevel.timeSensitive : InterruptionLevel.active,
    );

    final details = NotificationDetails(
      android: androidDetails,
      iOS: iosDetails,
    );

    await flutterLocalNotificationsPlugin.show(
      DateTime.now().millisecondsSinceEpoch ~/ 1000,
      title,
      body,
      details,
      payload: jsonEncode(data),
    );
    debugPrint('📱 Foreground notification (vibration: $vibrationEnabled)');
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

    try {
      final platform = Platform.isIOS ? 'ios' : (Platform.isAndroid ? 'android' : 'other');
      debugPrint('📱 Registering device: platform=$platform, token=${_fcmToken!.substring(0, 30)}...');
      
      final response = await http.post(
        Uri.parse('https://neptun.in.ua/api/register-device'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'token': _fcmToken,
          'regions': selectedRegions,
          'oblast_ids': selectedOblastIds,
          'raion_ids': selectedRaionIds,
          'device_id': _deviceId,
          'platform': platform,
        }),
      );

      if (response.statusCode == 200) {
        debugPrint('✅ Device registered successfully with ID: $_deviceId, platform: $platform');
      } else {
        debugPrint('❌ Failed to register device: ${response.statusCode}');
      }
    } catch (e) {
      debugPrint('❌ Error registering device: $e');
    }
  }

  Future<void> _unregisterDevice() async {
    if (_deviceId == null) return;

    try {
      // Send empty regions to effectively disable notifications
      final response = await http.post(
        Uri.parse('https://neptun.in.ua/api/register-device'),
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
        Uri.parse('https://neptun.in.ua/api/test-notification'),
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
    
    debugPrint('🔄 Migrating ${selectedRegions.length} regions to ID-based format');

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
    
    debugPrint('🔄 Migration complete: ${oblastIds.length} oblasts, ${raionIds.length} raions');
  }

  /// Update region subscriptions for push notifications
  /// Users will only receive alerts for regions they've selected
  Future<void> updateRegions(List<String> selectedRegions) async {
    final messaging = firebaseMessaging;
    if (messaging == null) {
      debugPrint('Firebase Messaging not available - cannot update regions');
      return;
    }

    debugPrint('📍 Updating region subscriptions: ${selectedRegions.length} regions');

    // Always clear stale subscriptions before re-subscribing
    await _unsubscribeFromAllTopics();

    final prefs = await SharedPreferences.getInstance();
    final regionDb = RegionDatabase()..initialize();
    await _migrateSelectionToIdsIfNeeded(prefs, selectedRegions, regionDb);

    // iOS: Verify APNs token is available before subscribing
    // Topic subscriptions on iOS REQUIRE APNs token
    if (Platform.isIOS) {
      String? apnsToken = await messaging.getAPNSToken();
      if (apnsToken == null) {
        debugPrint('🍎⚠️ iOS APNs token not available! Waiting...');
        // Wait and retry
        for (int i = 0; i < 15; i++) {
          await Future.delayed(const Duration(milliseconds: 500));
          apnsToken = await messaging.getAPNSToken();
          if (apnsToken != null) {
            debugPrint('🍎✅ APNs token received on retry ${i + 1}');
            break;
          }
          debugPrint('🍎⏳ APNs token retry ${i + 1}/15...');
        }
        if (apnsToken == null) {
          debugPrint('🍎❌ CRITICAL: APNs token still NULL after 15 retries!');
          debugPrint('🍎❌ Topic subscriptions will NOT work on this device!');
          debugPrint('🍎❌ Check: Push Notifications capability, Provisioning Profile, Physical device');
          // Continue anyway - the subscribeToTopic calls will fail but at least we tried
        }
      } else {
        debugPrint('🍎✅ APNs token available (${apnsToken.length} chars)');
      }
    }

    // Визначаємо на які ОБЛАСТІ треба підписатись (ID-based)
    final userOblastIds = prefs.getStringList('selected_oblast_ids')?.toSet() ?? <String>{};
    final legacyOblastId = prefs.getString('selected_oblast_id');
    if (legacyOblastId != null && legacyOblastId.isNotEmpty) {
      userOblastIds.add(legacyOblastId);
    }
    final userRaionIds = prefs.getStringList('selected_raion_ids')?.toSet() ?? <String>{};

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

    // FORCE unsubscribe from ALL topics first to avoid stale subscriptions
    // This prevents receiving notifications from regions user unselected
    debugPrint('🔄 Force unsubscribing from ALL topics before resubscription...');
    await _unsubscribeFromAllTopics();
    debugPrint('✅ Cleared all topic subscriptions');

    // Unsubscribe from topics that are no longer selected
    for (final topic in _subscribedTopics) {
      if (!newTopics.contains(topic)) {
        try {
          await messaging.unsubscribeFromTopic(topic);
          debugPrint('📤 Unsubscribed from topic: $topic');
        } catch (e) {
          debugPrint('Error unsubscribing from $topic: $e');
        }
      }
    }

    // Subscribe to new topics
    for (final topic in newTopics) {
      if (!_subscribedTopics.contains(topic)) {
        try {
          debugPrint('🔔 Attempting to subscribe to topic: $topic');
          await messaging.subscribeToTopic(topic);
          debugPrint('✅ Successfully subscribed to topic: $topic');
          if (Platform.isIOS) {
            debugPrint('🍎 iOS topic subscription SUCCESS: $topic');
          }
        } catch (e) {
          debugPrint('❌ Error subscribing to $topic: $e');
          if (Platform.isIOS) {
            debugPrint('🍎 iOS subscription FAILED for $topic - possible APNs configuration issue');
            debugPrint('🍎 Error details: $e');
          }
        }
      } else {
        debugPrint('ℹ️ Already subscribed to topic: $topic');
      }
    }

    // Subscribe to 'all_regions' topic ONLY if user selected ALL regions
    // This prevents users who selected specific regions from receiving all alerts
    // Count unique oblasts (24 oblasts + Kyiv = 25 regions with Firebase topics)
    const int totalRegions = 25;
    if (selectedRegions.length >= totalRegions) {
      try {
        await messaging.subscribeToTopic('all_regions');
        debugPrint('📥 Subscribed to all_regions topic (user selected all regions)');
      } catch (e) {
        debugPrint('Error subscribing to all_regions: $e');
      }
    } else {
      // Unsubscribe from all_regions if user didn't select all regions
      try {
        await messaging.unsubscribeFromTopic('all_regions');
        debugPrint('📤 Unsubscribed from all_regions topic (user has specific regions)');
      } catch (e) {
        debugPrint('Error unsubscribing from all_regions: $e');
      }
    }

    // Update tracked subscriptions
    _subscribedTopics = newTopics;

    // Save selected regions and subscribed topics to SharedPreferences
    try {
      await prefs.setStringList('selected_regions', selectedRegions);
      await prefs.setStringList('subscribed_topics', _subscribedTopics.toList());
      debugPrint('✅ Region subscriptions updated: ${_subscribedTopics.length} topics');
      debugPrint('📋 Final subscribed topics: $_subscribedTopics');
      if (Platform.isIOS) {
        debugPrint('🍎 iOS FINAL SUBSCRIPTIONS: $_subscribedTopics');
      }
    } catch (e) {
      debugPrint('Error saving subscribed topics: $e');
    }

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
      debugPrint('📋 Loaded ${_subscribedTopics.length} saved topic subscriptions');
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
      final blackoutNotificationsEnabled = prefs.getBool('blackout_notifications_enabled') ?? true;
      
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
      const AndroidNotificationChannel blackoutChannel = AndroidNotificationChannel(
        'blackout_alerts',
        'Відключення світла',
        description: 'Сповіщення про включення/відключення електроенергії',
        importance: Importance.high,
        playSound: true,
        enableVibration: true,
      );
      
      final androidPlugin = flutterLocalNotificationsPlugin
          .resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>();
      await androidPlugin?.createNotificationChannel(blackoutChannel);
      
      // Android notification details
      final androidDetails = AndroidNotificationDetails(
        channelId,
        'Відключення світла',
        channelDescription: 'Сповіщення про включення/відключення електроенергії',
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
      if (!Platform.isAndroid) return;
      
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
      final blackoutNotificationsEnabled = prefs.getBool('blackout_notifications_enabled') ?? true;
      
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
        channelDescription: 'Сповіщення про включення/відключення електроенергії',
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
