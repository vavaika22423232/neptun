import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'ballistic_alert_service.dart';
import 'live_activity_service.dart';
import 'sleep_mode_service.dart';
import 'widget_service.dart';
import 'region_database.dart';
import 'data_stream_service.dart';
import 'package:neptun_alarm_app/config/api_config.dart';
import 'package:neptun_alarm_app/core/network/http_retry.dart';

/// Сервіс відстеження тривог з ukrainealarm API
/// Показує сповіщення про "Повітряна тривога" / "Відбій" для обраних регіонів та районів
class AlarmTrackingService {
  static final AlarmTrackingService _instance =
      AlarmTrackingService._internal();
  factory AlarmTrackingService() => _instance;
  AlarmTrackingService._internal();

  Timer? _trackingTimer;
  bool _isTracking = false;

  final http.Client _httpClient = http.Client();

  // Попередній стан тривог для порівняння
  // Ключ: "oblast:ID" або "district:назва" -> hasAlarm
  final Map<String, bool> _previousAlarmStates = {};

  // Кеш дедуплікації: один ключ на регіон (не на threat type) — 5 хв
  final Map<String, DateTime> _notificationCache = {};
  static const Duration _notificationCacheDuration = Duration(minutes: 5);

  // Обмеження частоти: макс 3 сповіщення за хвилину; решта — в один batch
  static const int _maxNotificationsPerMinute = 3;
  final List<DateTime> _recentNotificationTimes = [];

  /// Mark an alarm region as recently notified via FCM push.
  /// Called from NotificationService to prevent AlarmTrackingService
  /// from showing a duplicate local notification.
  void markAlarmNotifiedByFcm(String regionName, {bool isStart = true}) {
    final prefix = isStart ? 'alarm' : 'clear';
    final cacheKey = '$prefix:$regionName';
    _notificationCache[cacheKey] = DateTime.now();
    // Also mark with wildcard threat type for alarm start
    if (isStart) {
      _notificationCache['alarm:$regionName:air'] = DateTime.now();
      _notificationCache['alarm:$regionName:ballistic'] = DateTime.now();
      _notificationCache['alarm:$regionName:drones'] = DateTime.now();
    }
    debugPrint('🔔 FCM dedup: marked $cacheKey as notified');
  }

  // Назви областей (regionId -> name)
  static const Map<String, String> _regionNames = {
    '1': 'Вінницька область',
    '2': 'Волинська область',
    '3': 'Дніпропетровська область',
    '4': 'Донецька область',
    '5': 'Житомирська область',
    '6': 'Закарпатська область',
    '7': 'Запорізька область',
    '8': 'Івано-Франківська область',
    '9': 'Київська область',
    '10': 'Кіровоградська область',
    '11': 'Луганська область',
    '12': 'Львівська область',
    '13': 'Миколаївська область',
    '14': 'Одеська область',
    '15': 'Полтавська область',
    '16': 'Рівненська область',
    '17': 'Сумська область',
    '18': 'Тернопільська область',
    '19': 'Харківська область',
    '20': 'Херсонська область',
    '21': 'Хмельницька область',
    '22': 'Черкаська область',
    '23': 'Чернівецька область',
    '24': 'Чернігівська область',
    '25': 'м. Київ',
    '26': 'АР Крим',
    '27': 'м. Севастополь',
  };

  // Reverse mapping: region name -> region ID
  static final Map<String, String> _regionNameToId = {
    for (var entry in _regionNames.entries) entry.value: entry.key,
    'Київ': '25', // Київ = м. Київ (НІКОЛИ Київська область!)
  };

  static const Map<String, String> _uaOblastIdToName = {
    'UA-05': 'Вінницька область',
    'UA-07': 'Волинська область',
    'UA-12': 'Дніпропетровська область',
    'UA-14': 'Донецька область',
    'UA-18': 'Житомирська область',
    'UA-21': 'Закарпатська область',
    'UA-23': 'Запорізька область',
    'UA-26': 'Івано-Франківська область',
    'UA-32': 'Київська область',
    'UA-35': 'Кіровоградська область',
    'UA-44': 'Луганська область',
    'UA-46': 'Львівська область',
    'UA-48': 'Миколаївська область',
    'UA-51': 'Одеська область',
    'UA-53': 'Полтавська область',
    'UA-56': 'Рівненська область',
    'UA-59': 'Сумська область',
    'UA-61': 'Тернопільська область',
    'UA-63': 'Харківська область',
    'UA-65': 'Херсонська область',
    'UA-68': 'Хмельницька область',
    'UA-71': 'Черкаська область',
    'UA-74': 'Чернігівська область',
    'UA-77': 'Чернівецька область',
    'UA-30': 'м. Київ',
    'UA-43': 'АР Крим',
    'UA-40': 'м. Севастополь',
  };

  final FlutterLocalNotificationsPlugin _localNotifications =
      FlutterLocalNotificationsPlugin();

  StreamSubscription? _alarmSSESub;

  /// Запустити відстеження тривог
  Future<void> startTracking() async {
    if (_isTracking) return;

    _isTracking = true;
    debugPrint('🔔 AlarmTrackingService: Starting alarm tracking');

    // Перше завантаження - без сповіщень (щоб заповнити _previousAlarmStates)
    await _fetchAndCompareAlarms(isInitial: true);

    // Subscribe to SSE for instant alarm updates (primary)
    final dataStream = DataStreamService.instance;
    dataStream.connect();
    _alarmSSESub = dataStream.alarmStream.listen((rawData) {
      _handlePushedAlarmData(rawData);
    });

    // Fallback таймер (SSE — основний канал, таймер — лише резерв)
    _trackingTimer = Timer.periodic(const Duration(seconds: 120), (_) {
      _fetchAndCompareAlarms(isInitial: false);
    });
  }

  /// Handle alarm data pushed via SSE — trigger comparison immediately
  void _handlePushedAlarmData(List<dynamic> rawData) {
    // SSE told us alarms changed — run the comparison cycle immediately
    // instead of waiting for the next timer tick
    _fetchAndCompareAlarms(isInitial: false);
  }

  /// Зупинити відстеження
  void stopTracking() {
    _trackingTimer?.cancel();
    _trackingTimer = null;
    _alarmSSESub?.cancel();
    _alarmSSESub = null;
    _isTracking = false;
    debugPrint('🔕 AlarmTrackingService: Stopped alarm tracking');
  }

  /// Отримати стан тривог та порівняти з попереднім
  Future<void> _fetchAndCompareAlarms({required bool isInitial}) async {
    try {
      final prefs = await SharedPreferences.getInstance();

      // Перевіряємо чи сповіщення увімкнені
      final notificationsEnabled =
          prefs.getBool('notifications_enabled') ?? true;
      if (!notificationsEnabled && !isInitial) {
        return;
      }

      final regionDb = RegionDatabase()..initialize();
      final selectedOblastIds =
          prefs.getStringList('selected_oblast_ids') ?? [];
      final selectedRaionIds = prefs.getStringList('selected_raion_ids') ?? [];
      final selectedRegionsLegacy =
          prefs.getStringList('selected_regions') ?? [];

      // Розділяємо на області та райони
      final selectedOblasts = <String>{}; // Назви областей
      final selectedDistricts = <String>{}; // Назви районів
      final oblastIdsToTrack = <String>{}; // ID областей для запиту (numeric)

      if (selectedOblastIds.isNotEmpty || selectedRaionIds.isNotEmpty) {
        for (final oblastId in selectedOblastIds) {
          final name =
              regionDb.getRegionNameById(oblastId) ??
              _uaOblastIdToName[oblastId];
          if (name != null) {
            selectedOblasts.add(name);
            final numericId = _regionNameToId[name];
            if (numericId != null) {
              oblastIdsToTrack.add(numericId);
            }
          }
        }

        for (final raionId in selectedRaionIds) {
          final name = regionDb.getRegionNameById(raionId);
          if (name != null) {
            selectedDistricts.add(name);
          }
          final parentOblastId = regionDb.getParentOblastId(raionId);
          final parentName = parentOblastId != null
              ? (regionDb.getRegionNameById(parentOblastId) ??
                    _uaOblastIdToName[parentOblastId])
              : null;
          if (parentName != null) {
            final numericId = _regionNameToId[parentName];
            if (numericId != null) {
              oblastIdsToTrack.add(numericId);
            }
          }
        }
      } else {
        if (selectedRegionsLegacy.isEmpty) {
          return;
        }
        for (final region in selectedRegionsLegacy) {
          if (region.contains('район')) {
            selectedDistricts.add(region);
            final oblast = _getOblastForDistrict(region);
            if (oblast != null) {
              final oblastId = _regionNameToId[oblast];
              if (oblastId != null) {
                oblastIdsToTrack.add(oblastId);
              }
            }
          } else {
            // Київ = м. Київ (канонічна назва для API)
            final canonical =
                (region == 'Київ') ? 'м. Київ' : region;
            selectedOblasts.add(canonical);
            final id = _regionNameToId[region] ?? _regionNameToId[canonical];
            if (id != null) {
              oblastIdsToTrack.add(id);
            }
          }
        }
      }

      if (oblastIdsToTrack.isEmpty && selectedDistricts.isEmpty) {
        return;
      }

      // Об'єднуємо вибрані області та райони
      final selectedRegions = {...selectedOblasts, ...selectedDistricts};

      debugPrint(
        '🔍 Tracking: oblasts=$selectedOblasts, districts=$selectedDistricts',
      );

      // Запит до API
      final http.Response response;
      try {
        response = await httpGetWithRetries(
          _httpClient,
          Uri.parse(ApiConfig.alarmsAll),
          timeout: const Duration(seconds: 10),
        );
      } on TimeoutException {
        debugPrint('⏱ AlarmTracking: API timeout, skipping cycle');
        return;
      } catch (_) {
        debugPrint('⚠️ AlarmTracking: network error, skipping cycle');
        return;
      }

      if (response.statusCode != 200) {
        return;
      }

      dynamic data;
      try {
        data = json.decode(response.body);
      } catch (_) {
        debugPrint('⚠️ AlarmTracking: invalid JSON (HTML?)');
        return;
      }
      final Map<String, bool> currentAlarms = {}; // key -> hasAlarm
      final Map<String, String> alarmTypes = {}; // key -> threat type
      final Map<String, String> alarmNames = {}; // key -> display name

      if (data is List) {
        for (final region in data) {
          final regionId = region['regionId']?.toString();
          final regionName = region['regionName']?.toString() ?? '';
          final regionType = region['regionType'] ?? '';
          final activeAlerts = region['activeAlerts'] as List? ?? [];

          if (regionId == null) continue;

          final hasAlarm = activeAlerts.isNotEmpty;

          // Визначаємо тип загрози
          String threatType = 'air';
          if (hasAlarm) {
            for (final alert in activeAlerts) {
              final alertType = alert['type']?.toString() ?? '';
              if (alertType == 'BALLISTIC' || alertType.contains('BALLISTIC')) {
                threatType = 'ballistic';
                break; // Балістика має найвищий пріоритет
              } else if (alertType == 'DRONES' || alertType.contains('DRONE')) {
                threatType = 'drones';
              }
            }
          }

          if (regionType == 'State') {
            // Це область
            if (!oblastIdsToTrack.contains(regionId)) continue;

            // Перевіряємо чи ОБЛАСТЬ обрана (а не тільки її райони)
            final oblastName = _regionNames[regionId] ?? regionName;
            if (selectedOblasts.contains(oblastName)) {
              final key = 'oblast:$regionId';
              currentAlarms[key] = hasAlarm;
              alarmTypes[key] = threatType;
              alarmNames[key] = oblastName;
            }
          } else if (regionType == 'District') {
            // Це район (або населений пункт з API)
            // Слобожанське → Чугуївський р-н, не Ізюмський!
            final effectiveDistrict =
                _getRaionForPlace(regionName) ?? _normalizeDistrictName(regionName);

            final oblastForDistrict = _getOblastForDistrict(effectiveDistrict);
            final isDistrictSelected = selectedDistricts.contains(effectiveDistrict);
            final isOblastSelected =
                oblastForDistrict != null &&
                selectedOblasts.contains(oblastForDistrict);

            if (isDistrictSelected || isOblastSelected) {
              final key = 'district:$effectiveDistrict';
              currentAlarms[key] = hasAlarm;
              alarmTypes[key] = threatType;
              alarmNames[key] = effectiveDistrict;
            }
          }
        }
      }

      // При першому завантаженні - просто зберігаємо стан
      if (isInitial) {
        _previousAlarmStates.clear();
        _previousAlarmStates.addAll(currentAlarms);
        debugPrint(
          '🔔 Initial alarm states loaded: ${currentAlarms.length} regions/districts',
        );

        // Оновлюємо віджет початковими даними
        await _updateWidget(
          currentAlarms,
          alarmTypes,
          alarmNames,
          selectedRegions.toList(),
          data,
        );
        return;
      }

      // Порівнюємо з попереднім станом, збираємо зміни
      final allKeys = {...currentAlarms.keys, ..._previousAlarmStates.keys};
      final List<({String name, String threatType})> alarmsStarted = [];
      final List<String> alarmsEnded = [];

      for (final key in allKeys) {
        final currentHasAlarm = currentAlarms[key] ?? false;
        final previousHasAlarm = _previousAlarmStates[key] ?? false;

        if (currentHasAlarm != previousHasAlarm) {
          final displayName = alarmNames[key] ?? key.split(':').last;
          final threatType = alarmTypes[key] ?? 'air';

          if (currentHasAlarm) {
            alarmsStarted.add((name: displayName, threatType: threatType));
          } else {
            alarmsEnded.add(displayName);
          }
        }
      }

      // Показуємо сповіщення: batch якщо багато, інакше окремо
      final hasAnyActiveAlarm = currentAlarms.values.any((v) => v);
      await _notifyAlarmsBatch(
        alarmsStarted,
        alarmsEnded,
        hasAnyActiveAlarm: hasAnyActiveAlarm,
      );

      // Оновлюємо попередній стан
      _previousAlarmStates.clear();
      _previousAlarmStates.addAll(currentAlarms);

      // Оновлюємо віджет
      await _updateWidget(
        currentAlarms,
        alarmTypes,
        alarmNames,
        selectedRegions.toList(),
        data,
      );
    } catch (e) {
      debugPrint('AlarmTrackingService error: $e');
    }
  }

  /// Нормалізує назву району з API до формату в налаштуваннях
  String _normalizeDistrictName(String apiName) {
    // API може повертати "Харківський" або "Харківський район"
    String name = apiName.trim();
    if (!name.contains('район')) {
      name = '$name район';
    }
    return name;
  }

  /// Знаходить область для району
  String? _getOblastForDistrict(String districtName) {
    for (final entry in _oblastToDistricts.entries) {
      if (entry.value.contains(districtName)) {
        return entry.key;
      }
    }
    return null;
  }

  /// Населені пункти, що належать іншому району ніж можна припустити.
  /// Ключ — назва, значення — правильний район (формат "Чугуївський район").
  static const Map<String, String> _placeToRaion = {
    'Слобожанське': 'Чугуївський район',  // Слобожанська МТГ — Чугуївський р-н, НЕ Ізюмський!
  };

  /// Отримати район для населеного пункту (для точного фільтру).
  String? _getRaionForPlace(String placeName) => _placeToRaion[placeName];

  /// Оновлює віджет на робочому столі
  Future<void> _updateWidget(
    Map<String, bool> currentAlarms,
    Map<String, String> alarmTypes,
    Map<String, String> alarmNames,
    List<String> selectedRegions,
    dynamic apiData,
  ) async {
    if (!Platform.isAndroid && !Platform.isIOS) return;

    try {
      // Чи є тривога в обраних регіонах
      final hasAlarm = currentAlarms.values.any((v) => v);

      // Кількість загроз в обраних регіонах
      final threatsCount = currentAlarms.values.where((v) => v).length;

      // Тип загрози (пріоритет: ballistic > drones > air)
      String mainThreatType = '';
      if (hasAlarm) {
        for (final entry in alarmTypes.entries) {
          if (currentAlarms[entry.key] == true) {
            if (entry.value == 'ballistic') {
              mainThreatType = 'Ракетна загроза';
              break;
            } else if (entry.value == 'drones') {
              mainThreatType = 'Загроза БПЛА';
            } else if (mainThreatType.isEmpty) {
              mainThreatType = 'Повітряна тривога';
            }
          }
        }
      }

      // Загальна кількість тривог по Україні
      int totalAlarmsInUkraine = 0;
      if (apiData is List) {
        for (final region in apiData) {
          final regionType = region['regionType'] ?? '';
          final activeAlerts = region['activeAlerts'] as List? ?? [];
          if (regionType == 'State' && activeAlerts.isNotEmpty) {
            totalAlarmsInUkraine++;
          }
        }
      }

      // Назва регіону для відображення
      String displayRegion = selectedRegions.isNotEmpty
          ? selectedRegions.first
          : 'Україна';
      // Скорочуємо назву області
      displayRegion = displayRegion
          .replaceAll(' область', '')
          .replaceAll('м. ', '');

      // Отримуємо детальну інформацію про загрози
      final threatDetails = await _fetchThreatDetails();

      // Оновлюємо віджет
      await WidgetService().updateWidget(
        region: displayRegion,
        isAlarm: hasAlarm,
        threatsCount: threatsCount,
        timerMinutes: 0,
        totalAlarms: totalAlarmsInUkraine,
        threatType: mainThreatType,
        dronesCount: threatDetails['drones'] ?? 0,
        missilesCount: threatDetails['missiles'] ?? 0,
        kabCount: threatDetails['kab'] ?? 0,
        ballisticCount: threatDetails['ballistic'] ?? 0,
        totalThreats: threatDetails['total'] ?? 0,
      );

      debugPrint(
        '📱 Widget updated: alarm=$hasAlarm, drones=${threatDetails['drones']}, missiles=${threatDetails['missiles']}, kab=${threatDetails['kab']}',
      );
    } catch (e) {
      debugPrint('Widget update error in AlarmTrackingService: $e');
    }
  }

  /// Отримує детальну інформацію про активні загрози
  Future<Map<String, int>> _fetchThreatDetails() async {
    try {
      final http.Response response;
      try {
        response = await httpGetWithRetries(
          _httpClient,
          Uri.parse(ApiConfig.threats),
          timeout: const Duration(seconds: 5),
        );
      } on TimeoutException {
        return {
          'drones': 0,
          'missiles': 0,
          'kab': 0,
          'ballistic': 0,
          'total': 0,
        };
      } catch (_) {
        return {
          'drones': 0,
          'missiles': 0,
          'kab': 0,
          'ballistic': 0,
          'total': 0,
        };
      }

      if (response.statusCode != 200) {
        return {
          'drones': 0,
          'missiles': 0,
          'kab': 0,
          'ballistic': 0,
          'total': 0,
        };
      }

      dynamic data;
      try {
        data = json.decode(response.body);
      } catch (_) {
        return {
          'drones': 0,
          'missiles': 0,
          'kab': 0,
          'ballistic': 0,
          'total': 0,
        };
      }

      // Try to get from summary first (new format)
      final summary = data['summary'] as Map<String, dynamic>?;
      if (summary != null) {
        return {
          'drones': summary['drones'] as int? ?? 0,
          'missiles': summary['missiles'] as int? ?? 0,
          'kab': summary['kab'] as int? ?? 0,
          'ballistic': summary['ballistic'] as int? ?? 0,
          'total': summary['total'] as int? ?? 0,
        };
      }

      // Fallback: parse from threats array
      final threats = data['threats'] as List? ?? [];

      int drones = 0;
      int missiles = 0;
      int kab = 0;
      int ballistic = 0;

      for (final threat in threats) {
        final type = threat['threat_type']?.toString().toLowerCase() ?? '';
        final quantity =
            threat['quantity_remaining'] as int? ??
            threat['quantity'] as int? ??
            1;

        if (type == 'drone' || type == 'shahed') {
          drones += quantity;
        } else if (type == 'missile' ||
            type == 'cruise_missile' ||
            type == 'cruise') {
          missiles += quantity;
        } else if (type == 'kab') {
          kab += quantity;
        } else if (type == 'ballistic') {
          ballistic += quantity;
        }
      }

      return {
        'drones': drones,
        'missiles': missiles,
        'kab': kab,
        'ballistic': ballistic,
        'total': drones + missiles + kab + ballistic,
      };
    } catch (e) {
      debugPrint('Error fetching threat details: $e');
      return {'drones': 0, 'missiles': 0, 'kab': 0, 'ballistic': 0, 'total': 0};
    }
  }

  /// Batch-сповіщення: один показ для багатьох регіонів якщо їх > 3
  Future<void> _notifyAlarmsBatch(
    List<({String name, String threatType})> started,
    List<String> ended, {
    bool hasAnyActiveAlarm = false,
  }) async {
    _trimRecentNotificationTimes();

    for (final item in started) {
      debugPrint('🚨 ALARM STARTED: ${item.name} (type: ${item.threatType})');
    }
    for (final name in ended) {
      debugPrint('✅ ALARM ENDED: $name');
    }

    // Alarm started: один ключ на регіон, batch якщо багато (4+)
    final toNotifyStarted = started
        .where((e) => !_wasRecentlyNotified('alarm:${e.name}'))
        .toList();
    final toNotifyEnded = ended
        .where((n) => !_wasRecentlyNotified('clear:$n'))
        .toList();
    if (toNotifyStarted.isEmpty && toNotifyEnded.isEmpty) return;

    if (toNotifyStarted.length == 1) {
      await _notifyAlarmStarted(
        toNotifyStarted.first.name,
        toNotifyStarted.first.threatType,
      );
      unawaited(LiveActivityService().start(
        region: toNotifyStarted.first.name,
        threatType: toNotifyStarted.first.threatType,
      ));
    } else if (toNotifyStarted.length > 1) {
      final names = toNotifyStarted.map((e) => e.name).join(', ');
      final threatType = toNotifyStarted.any((e) => e.threatType == 'ballistic')
          ? 'ballistic'
          : toNotifyStarted.any((e) => e.threatType == 'drones')
              ? 'drones'
              : 'air';
      await _notifyAlarmStarted(names, threatType);
      unawaited(LiveActivityService().start(
        region: names,
        threatType: threatType,
      ));
      for (final e in toNotifyStarted) {
        _markAsNotified('alarm:${e.name}');
      }
    }

    if (toNotifyEnded.length == 1) {
      await _notifyAlarmEnded(toNotifyEnded.first);
      if (!hasAnyActiveAlarm) {
        unawaited(LiveActivityService().end());
      }
    } else if (toNotifyEnded.length > 1) {
      final names = toNotifyEnded.join(', ');
      await _notifyAlarmEnded(names);
      if (!hasAnyActiveAlarm) {
        unawaited(LiveActivityService().end());
      }
      for (final n in toNotifyEnded) {
        _markAsNotified('clear:$n');
      }
    }
  }

  void _trimRecentNotificationTimes() {
    final cutoff = DateTime.now().subtract(const Duration(minutes: 1));
    _recentNotificationTimes.removeWhere((t) => t.isBefore(cutoff));
  }

  /// Сповіщення про початок тривоги
  Future<void> _notifyAlarmStarted(String regionName, String threatType) async {
    // Один ключ на регіон (не на threat type) — 5 хв
    final cacheKey = 'alarm:$regionName';
    if (_wasRecentlyNotified(cacheKey)) {
      debugPrint('🔔 Skipping duplicate: $regionName');
      return;
    }
    _markAsNotified(cacheKey);

    // Rate limit: макс 3 за хвилину
    if (_recentNotificationTimes.length >= _maxNotificationsPerMinute) {
      debugPrint('🔔 Rate limit: skipping (${_recentNotificationTimes.length} in last min)');
      return;
    }
    _recentNotificationTimes.add(DateTime.now());

    final prefs = await SharedPreferences.getInstance();

    // Persist stats for analytics page
    final totalAlarms = (prefs.getInt('stats_total_alarms') ?? 0) + 1;
    await prefs.setInt('stats_total_alarms', totalAlarms);
    final safeKey = regionName.replaceAll(RegExp(r'[^a-zA-Zа-яА-ЯіІїЇєЄґҐ0-9]'), '_');
    await prefs.setString('alarm_start_$safeKey', DateTime.now().toIso8601String());
    final notificationsEnabled = prefs.getBool('notifications_enabled') ?? true;
    final allowed = _isThreatTypeAllowed(prefs, threatType);
    if (!allowed) {
      debugPrint('🔕 Threat type $threatType disabled by user settings');
      return;
    }

    // Визначаємо текст та емодзі
    String emoji = '🚨';
    String threatText = 'Повітряна тривога';

    if (threatType == 'ballistic') {
      emoji = '🚀';
      threatText = 'Ракетна небезпека';
      // Показуємо банер балістичної загрози
      BallisticAlertService().triggerBallisticThreat(region: regionName);
    } else if (threatType == 'drones') {
      emoji = '🛩️';
      threatText = 'Загроза БПЛА';
    }

    final title = '$emoji $regionName';
    final body = '$threatText! Негайно в укриття!';

    // Режим сну: не показувати сповіщення вночі
    final shouldBlockSleep =
        await SleepModeService.shouldBlockNotificationStatic(body);
    if (shouldBlockSleep) {
      debugPrint('🌙 Sleep mode active - blocking alarm tracking notification');
      return;
    }

    // Показуємо локальне сповіщення
    if (notificationsEnabled) {
      await _showLocalNotification(
        title: title,
        body: body,
        isAlarm: true,
        isCritical: threatType == 'ballistic',
      );
    }
  }

  /// Сповіщення про відбій тривоги
  Future<void> _notifyAlarmEnded(String regionName) async {
    final cacheKey = 'clear:$regionName';
    if (_wasRecentlyNotified(cacheKey)) {
      debugPrint('🔔 Skipping duplicate all-clear notification: $regionName');
      return;
    }
    _markAsNotified(cacheKey);

    // Rate limit: макс 3 за хвилину (разом з alarm started)
    _trimRecentNotificationTimes();
    if (_recentNotificationTimes.length >= _maxNotificationsPerMinute) {
      debugPrint('🔔 Rate limit: skipping all-clear for $regionName');
      return;
    }
    _recentNotificationTimes.add(DateTime.now());

    final prefs = await SharedPreferences.getInstance();

    final safeKey = regionName.replaceAll(RegExp(r'[^a-zA-Zа-яА-ЯіІїЇєЄґҐ0-9]'), '_');
    final startStr = prefs.getString('alarm_start_$safeKey');
    if (startStr != null) {
      final start = DateTime.tryParse(startStr);
      if (start != null) {
        final minutes = DateTime.now().difference(start).inMinutes;
        if (minutes > 0) {
          final total = (prefs.getInt('stats_total_minutes') ?? 0) + minutes;
          await prefs.setInt('stats_total_minutes', total);
        }
      }
      // Accumulate alarm count per region for heatmap (PRO)
      final heatmapKey = 'heatmap_count_$safeKey';
      await prefs.setInt(heatmapKey, (prefs.getInt(heatmapKey) ?? 0) + 1);
      await prefs.remove('alarm_start_$safeKey');
    }
    final notificationsEnabled = prefs.getBool('notifications_enabled') ?? true;
    final allowed = _isThreatTypeAllowed(prefs, 'air');
    if (!allowed) {
      debugPrint('🔕 Threat type air disabled by user settings');
      return;
    }

    final title = '✅ $regionName';
    final body = 'Відбій повітряної тривоги';

    // Режим сну: не показувати сповіщення вночі
    final shouldBlockSleep =
        await SleepModeService.shouldBlockNotificationStatic(body);
    if (shouldBlockSleep) {
      debugPrint(
          '🌙 Sleep mode active - blocking all-clear tracking notification');
      return;
    }

    // Показуємо локальне сповіщення
    if (notificationsEnabled) {
      await _showLocalNotification(
        title: title,
        body: body,
        isAlarm: false,
        isCritical: false,
      );
    }
  }

  bool _isThreatTypeAllowed(SharedPreferences prefs, String threatType) {
    final allowed = prefs.getStringList('notify_threat_types') ?? [];
    if (allowed.isEmpty) return true;
    String key = 'air';
    if (threatType == 'ballistic') key = 'ballistic';
    if (threatType == 'drones') key = 'drones';
    return allowed.contains(key);
  }

  /// Показати локальне сповіщення
  Future<void> _showLocalNotification({
    required String title,
    required String body,
    required bool isAlarm,
    required bool isCritical,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    final vibrationEnabled = prefs.getBool('vibration_enabled') ?? true;

    // Використовуємо різні канали для режимів з/без вібрації
    // Це потрібно бо Android кешує налаштування каналу при створенні
    final vibSuffix = vibrationEnabled ? '' : '_silent';

    String channelId;
    String channelName;
    Color color;

    if (isAlarm) {
      if (isCritical) {
        channelId = 'critical_alerts$vibSuffix';
        channelName = vibrationEnabled
            ? 'Критичні тривоги'
            : 'Критичні тривоги (без вібро)';
        color = const Color(0xFFE63946);
      } else {
        channelId = 'normal_alerts$vibSuffix';
        channelName = vibrationEnabled
            ? 'Звичайні тривоги'
            : 'Звичайні тривоги (без вібро)';
        color = const Color(0xFFFF9500);
      }
    } else {
      channelId = 'all_clear_alerts$vibSuffix';
      channelName = vibrationEnabled
          ? 'Відбій тривоги'
          : 'Відбій тривоги (без вібро)';
      color = const Color(0xFF30D158);
    }

    final androidDetails = AndroidNotificationDetails(
      channelId,
      channelName,
      channelDescription: isAlarm ? 'Сповіщення про тривогу' : 'Відбій тривоги',
      importance: isCritical ? Importance.max : Importance.high,
      priority: isCritical ? Priority.max : Priority.high,
      color: color,
      colorized: true,
      playSound: true,
      enableVibration: vibrationEnabled,
      category: isAlarm
          ? AndroidNotificationCategory.alarm
          : AndroidNotificationCategory.message,
      visibility: NotificationVisibility.public,
    );

    final iosDetails = DarwinNotificationDetails(
      presentAlert: true,
      presentBadge: true,
      presentSound: true,
      interruptionLevel: isCritical
          ? InterruptionLevel.timeSensitive
          : InterruptionLevel.active,
    );

    final details = NotificationDetails(
      android: androidDetails,
      iOS: iosDetails,
    );

    // Використовуємо стабільний ID на основі назви регіону
    // Це дозволяє оновлювати існуюче сповіщення замість створення нового
    final notificationId = title.hashCode.abs() % 100000;

    await _localNotifications.show(notificationId, title, body, details);
  }

  /// Перевіряє чи сповіщення було нещодавно показано
  bool _wasRecentlyNotified(String cacheKey) {
    final lastNotified = _notificationCache[cacheKey];
    if (lastNotified == null) return false;
    return DateTime.now().difference(lastNotified) < _notificationCacheDuration;
  }

  /// Позначає сповіщення як показане
  void _markAsNotified(String cacheKey) {
    _notificationCache[cacheKey] = DateTime.now();
    // Очищаємо старі записи
    final now = DateTime.now();
    _notificationCache.removeWhere(
      (key, time) => now.difference(time) > const Duration(minutes: 5),
    );
  }

  /// Отримати поточні дані тривоги для віджета
  Future<Map<String, dynamic>> getCurrentAlarmData() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final selectedRegions = prefs.getStringList('selected_regions') ?? [];

      // Отримуємо стан тривог через API
      final http.Response response;
      try {
        response = await httpGetWithRetries(
          _httpClient,
          Uri.parse(ApiConfig.alarmsAll),
          timeout: const Duration(seconds: 10),
        );
      } on TimeoutException {
        return _getDefaultAlarmData();
      } catch (_) {
        return _getDefaultAlarmData();
      }

      if (response.statusCode != 200) {
        return _getDefaultAlarmData();
      }

      dynamic data;
      try {
        data = json.decode(response.body);
      } catch (_) {
        return _getDefaultAlarmData();
      }

      // Підраховуємо тривоги
      int alarmsInSelectedRegions = 0;
      bool hasAlarm = false;
      String displayRegion = 'Всі регіони';

      if (selectedRegions.isNotEmpty) {
        displayRegion = selectedRegions.length == 1
            ? selectedRegions.first
            : '${selectedRegions.length} регіонів';

        if (data is List) {
          for (final regionData in data) {
            final regionName = regionData['regionName'] as String?;
            final regionType = regionData['regionType'] as String?;
            final activeAlerts = regionData['activeAlerts'] as List?;
            final isActive = activeAlerts != null && activeAlerts.isNotEmpty;

            if (regionName == null || !isActive) continue;

            if (regionType == 'State' && selectedRegions.contains(regionName)) {
              alarmsInSelectedRegions++;
              hasAlarm = true;
            } else if (regionType == 'District') {
              final oblast = _getOblastForDistrict(regionName);
              if (oblast != null && selectedRegions.contains(oblast)) {
                alarmsInSelectedRegions++;
                hasAlarm = true;
              }
              if (selectedRegions.contains(regionName)) {
                alarmsInSelectedRegions++;
                hasAlarm = true;
              }
            }
          }
        }
      }

      // Загальна кількість тривог
      int totalAlarmsInUkraine = 0;
      if (data is List) {
        totalAlarmsInUkraine = data
            .where((r) => (r['activeAlerts'] as List?)?.isNotEmpty ?? false)
            .length;
      }

      // Отримуємо детальну інформацію про загрози
      final threatDetails = await _fetchThreatDetails();

      return {
        'region': displayRegion,
        'isAlarm': hasAlarm,
        'threatsCount': alarmsInSelectedRegions,
        'timerMinutes': 0,
        'totalAlarms': totalAlarmsInUkraine,
        'threatType': '',
        'dronesCount': threatDetails['drones'] ?? 0,
        'missilesCount': threatDetails['missiles'] ?? 0,
        'kabCount': threatDetails['kab'] ?? 0,
        'ballisticCount': threatDetails['ballistic'] ?? 0,
        'totalThreats': threatDetails['total'] ?? 0,
      };
    } catch (e) {
      debugPrint('❌ Error getting current alarm data: $e');
      return _getDefaultAlarmData();
    }
  }

  Map<String, dynamic> _getDefaultAlarmData() {
    return {
      'region': 'Всі регіони',
      'isAlarm': false,
      'threatsCount': 0,
      'timerMinutes': 0,
      'totalAlarms': 0,
      'threatType': '',
      'dronesCount': 0,
      'missilesCount': 0,
      'kabCount': 0,
      'ballisticCount': 0,
      'totalThreats': 0,
    };
  }
}

/// Повний маппінг областей до їх районів
const Map<String, List<String>> _oblastToDistricts = {
  'Харківська область': [
    'Харківський район',
    'Куп\'янський район',
    'Ізюмський район',
    'Чугуївський район',
    'Богодухівський район',
    'Красноградський район',
    'Лозівський район',
  ],
  'Донецька область': [
    'Краматорський район',
    'Бахмутський район',
    'Покровський район',
    'Волноваський район',
    'Кальміуський район',
    'Маріупольський район',
    'Донецький район',
    'Горлівський район',
  ],
  'Запорізька область': [
    'Запорізький район',
    'Мелітопольський район',
    'Бердянський район',
    'Пологівський район',
    'Василівський район',
  ],
  'Херсонська область': [
    'Херсонський район',
    'Бериславський район',
    'Генічеський район',
    'Каховський район',
    'Скадовський район',
  ],
  'Луганська область': [
    'Сєвєродонецький район',
    'Старобільський район',
    'Сватівський район',
    'Щастинський район',
  ],
  'Сумська область': [
    'Сумський район',
    'Конотопський район',
    'Шосткинський район',
    'Охтирський район',
    'Роменський район',
  ],
  'Дніпропетровська область': [
    'Дніпровський район',
    'Криворізький район',
    'Кам\'янський район',
    'Нікопольський район',
    'Павлоградський район',
    'Синельниківський район',
    'Новомосковський район',
  ],
  'Миколаївська область': [
    'Миколаївський район',
    'Баштанський район',
    'Вознесенський район',
    'Первомайський район',
  ],
  'Одеська область': [
    'Одеський район',
    'Білгород-Дністровський район',
    'Болградський район',
    'Ізмаїльський район',
    'Подільський район',
    'Березівський район',
    'Роздільнянський район',
  ],
  'Полтавська область': [
    'Полтавський район',
    'Кременчуцький район',
    'Лубенський район',
    'Миргородський район',
  ],
  'Київська область': [
    'Білоцерківський район',
    'Бориспільський район',
    'Броварський район',
    'Бучанський район',
    'Вишгородський район',
    'Обухівський район',
    'Фастівський район',
  ],
  'Чернігівська область': [
    'Чернігівський район',
    'Новгород-Сіверський район',
    'Ніжинський район',
    'Прилуцький район',
    'Корюківський район',
  ],
  'Черкаська область': [
    'Черкаський район',
    'Золотоніський район',
    'Уманський район',
    'Звенигородський район',
  ],
  'Кіровоградська область': [
    'Кропивницький район',
    'Олександрійський район',
    'Голованівський район',
    'Новоукраїнський район',
  ],
  'Вінницька область': [
    'Вінницький район',
    'Гайсинський район',
    'Жмеринський район',
    'Могилів-Подільський район',
    'Тульчинський район',
    'Хмільницький район',
  ],
  'Житомирська область': [
    'Житомирський район',
    'Бердичівський район',
    'Коростенський район',
    'Звягельський район',
  ],
  'Рівненська область': [
    'Рівненський район',
    'Дубенський район',
    'Вараський район',
    'Сарненський район',
  ],
  'Волинська область': [
    'Луцький район',
    'Володимирський район',
    'Ковельський район',
    'Камінь-Каширський район',
  ],
  'Тернопільська область': [
    'Тернопільський район',
    'Чортківський район',
    'Кременецький район',
  ],
  'Хмельницька область': [
    'Хмельницький район',
    'Шепетівський район',
    'Кам\'янець-Подільський район',
  ],
  'Львівська область': [
    'Львівський район',
    'Стрийський район',
    'Самбірський район',
    'Дрогобицький район',
    'Червоноградський район',
    'Яворівський район',
    'Золочівський район',
  ],
  'Івано-Франківська область': [
    'Івано-Франківський район',
    'Калуський район',
    'Коломийський район',
    'Косівський район',
    'Надвірнянський район',
    'Верховинський район',
  ],
  'Закарпатська область': [
    'Ужгородський район',
    'Мукачівський район',
    'Берегівський район',
    'Хустський район',
    'Рахівський район',
    'Тячівський район',
  ],
  'Чернівецька область': [
    'Чернівецький район',
    'Вижницький район',
    'Дністровський район',
  ],
  'м. Київ': [],
};
