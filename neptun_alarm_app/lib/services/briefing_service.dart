import 'dart:convert';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:neptun_alarm_app/config/api_config.dart';
import 'package:neptun_alarm_app/core/network/http_retry.dart';
import 'package:neptun_alarm_app/core/utils/app_debug_log.dart';
import 'package:neptun_alarm_app/config/prefs_keys.dart';
import 'region_database.dart';

/// Aggregates daily stats for the briefing feature.
/// Caches data and can trigger local notifications at 8:00 and 21:00.
class BriefingService {
  static final BriefingService _instance = BriefingService._internal();
  factory BriefingService() => _instance;
  BriefingService._internal();

  BriefingData? _cached;
  DateTime? _cacheTime;
  static const _cacheDuration = Duration(minutes: 15);
  static const _cacheMaxAge = Duration(hours: 24);
  static const _cacheKey = 'briefing_offline_cache';
  static const _cacheTsKey = 'briefing_offline_cache_ts';

  /// Fetch briefing data (today's alarms, threats, user region stats).
  /// Returns cached data when offline (up to 24h old).
  /// Alarms and threats fetched independently — one API failure doesn't break the other.
  Future<BriefingData> fetchBriefing() async {
    if (_cached != null &&
        _cacheTime != null &&
        DateTime.now().difference(_cacheTime!) < _cacheDuration) {
      return _cached!;
    }

    final client = http.Client();
    try {
      final prefs = await SharedPreferences.getInstance();

      // Паралельно завантажуємо обидва джерела — один fail не ламає інший
      var alarmsData = <String, dynamic>{};
      var threatsData = <String, dynamic>{};
      var alarmsOk = false;
      var threatsOk = false;
      final alarmsFuture = httpGetWithRetries(
        client,
        Uri.parse(ApiConfig.alarmsAll),
        timeout: ApiConfig.httpTimeout,
      );
      final threatsFuture = httpGetWithRetries(
        client,
        Uri.parse('${ApiConfig.threats}?timeRange=1440'),
        timeout: ApiConfig.httpTimeout,
      );

      try {
        final r = await alarmsFuture;
        if (r.statusCode == 200) {
          final d = jsonDecode(r.body);
          alarmsData = d is Map
              ? Map<String, dynamic>.from(d)
              : <String, dynamic>{'list': d};
          alarmsOk = true;
        }
      } catch (e) {
        appDebugLog('BriefingService alarms fetch failed: $e');
      }
      try {
        final r = await threatsFuture;
        if (r.statusCode == 200) {
          final decoded = jsonDecode(r.body);
          threatsData = decoded is Map
              ? Map<String, dynamic>.from(decoded)
              : <String, dynamic>{};
          threatsOk = true;
        }
      } catch (e) {
        appDebugLog('BriefingService threats fetch failed: $e');
      }

      // Обидва API впали — беремо офлайн кеш
      if (!alarmsOk && !threatsOk) {
        final cached = await _loadOfflineCache();
        if (cached != null) return cached;
      }

      int totalAlarmsToday = 0;
      final alarmRegions = <String>[];
      final list = alarmsData['list'] ?? alarmsData;
      final regionsList = list is List
          ? list
          : (alarmsData['regions'] as List? ?? []);
      for (final r in regionsList) {
        if (r is! Map) continue;
        final alerts = r['activeAlerts'] as List? ?? [];
        if (alerts.isNotEmpty) {
          totalAlarmsToday++;
          final name = r['regionName']?.toString() ?? '';
          if (name.isNotEmpty) alarmRegions.add(name);
        }
      }

      int drones = 0, missiles = 0, kab = 0, ballistic = 0;
      final s = threatsData['summary'];
      if (s is Map) {
        drones = (s['drones'] as num?)?.toInt() ?? 0;
        missiles = (s['missiles'] as num?)?.toInt() ?? 0;
        kab = (s['kab'] as num?)?.toInt() ?? 0;
        ballistic = (s['ballistic'] as num?)?.toInt() ?? 0;
      }

      final hour = DateTime.now().hour;
      final isMorning = hour < 12;

      // Збір назв регіонів користувача: selected_regions (names) + oblast/raion IDs через RegionDatabase
      final regionDb = RegionDatabase()..initialize();
      final userOblastNames = <String>{};
      final namesFromPrefs = prefs.getStringList(PrefsKeys.selectedRegions) ?? [];
      for (final n in namesFromPrefs) {
        final t = n.trim();
        if (t.isNotEmpty) {
          userOblastNames.add(t);
          userOblastNames.add(t.replaceAll(' область', '').trim());
        }
      }
      for (final id in prefs.getStringList('selected_oblast_ids') ?? []) {
        final name = regionDb.getOblastById(id)?.nameUk;
        if (name != null) {
          userOblastNames.add(name);
          userOblastNames.add(name.replaceAll(' область', '').trim());
        }
      }
      for (final raionId in prefs.getStringList('selected_raion_ids') ?? []) {
        final oblastId = regionDb.getOblastIdForRaion(raionId);
        if (oblastId != null) {
          final name = regionDb.getOblastById(oblastId)?.nameUk;
          if (name != null) {
            userOblastNames.add(name);
            userOblastNames.add(name.replaceAll(' область', '').trim());
          }
        }
      }

      bool matches(String apiName) {
        final n = apiName.trim();
        if (userOblastNames.contains(n)) return true;
        final short = n.replaceAll(' область', '').trim();
        return userOblastNames.contains(short);
      }

      final userRegionAlarmCount = alarmRegions.where(matches).length;
      final totalSelected =
          namesFromPrefs.length +
          (prefs.getStringList('selected_oblast_ids') ?? []).length +
          (prefs.getStringList('selected_raion_ids') ?? []).length;

      String? displayRegion;
      if (namesFromPrefs.isNotEmpty) {
        displayRegion = namesFromPrefs.first;
      } else {
        final oblastIds = prefs.getStringList('selected_oblast_ids');
        if (oblastIds != null && oblastIds.isNotEmpty) {
          displayRegion = regionDb.getOblastById(oblastIds.first)?.nameUk;
        }
        if (displayRegion == null) {
          final raionIds = prefs.getStringList('selected_raion_ids');
          if (raionIds != null && raionIds.isNotEmpty) {
            final obId = regionDb.getOblastIdForRaion(raionIds.first);
            displayRegion = obId != null
                ? regionDb.getOblastById(obId)?.nameUk
                : null;
          }
        }
      }

      _cached = BriefingData(
        isMorning: isMorning,
        totalAlarmsToday: totalAlarmsToday,
        alarmRegions: alarmRegions,
        drones: drones,
        missiles: missiles,
        kab: kab,
        ballistic: ballistic,
        userRegionName: displayRegion,
        userRegionAlarmCount: userRegionAlarmCount,
        userRegionsTotal: totalSelected,
      );
      _cacheTime = DateTime.now();

      // Зберігаємо для офлайн-режиму
      try {
        await prefs.setString(_cacheKey, jsonEncode(_cached!.toJson()));
        await prefs.setInt(_cacheTsKey, DateTime.now().millisecondsSinceEpoch);
      } catch (_) {}

      return _cached!;
    } catch (e) {
      appDebugLog('BriefingService error: $e');
      final cached = await _loadOfflineCache();
      if (cached != null) return cached;
      return BriefingData(
        isMorning: DateTime.now().hour < 12,
        totalAlarmsToday: 0,
        alarmRegions: [],
        drones: 0,
        missiles: 0,
        kab: 0,
        ballistic: 0,
        userRegionName: null,
        userRegionAlarmCount: 0,
        userRegionsTotal: 0,
      );
    } finally {
      client.close();
    }
  }

  Future<BriefingData?> _loadOfflineCache() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final ts = prefs.getInt(_cacheTsKey);
      if (ts == null) return null;
      final age = DateTime.now().millisecondsSinceEpoch - ts;
      if (age > _cacheMaxAge.inMilliseconds) return null;
      final json = prefs.getString(_cacheKey);
      if (json == null) return null;
      final data = jsonDecode(json) as Map<String, dynamic>;
      return BriefingData.fromJson(data);
    } catch (_) {
      return null;
    }
  }

  /// Invalidate cache (e.g. when user changes regions).
  void invalidateCache() {
    _cached = null;
    _cacheTime = null;
  }

  static const _briefingDateKey = 'briefing_last_sent_date';
  static const _briefingChannelId = 'morning_briefing';
  static const _briefingNotifId = 9901;

  /// Check whether a morning briefing push should be sent (8:00–10:00, once per day).
  /// Call on app foreground / resume and after NotificationService.initialize().
  static Future<void> scheduleNotifications(
    FlutterLocalNotificationsPlugin plugin,
  ) async {
    try {
      final now = DateTime.now();
      final hour = now.hour;
      // Only fire in the 8:00–10:00 window
      if (hour < 8 || hour >= 10) return;

      final prefs = await SharedPreferences.getInstance();
      final lastSent = prefs.getString(_briefingDateKey) ?? '';
      final today = '${now.year}-${now.month.toString().padLeft(2, '0')}-${now.day.toString().padLeft(2, '0')}';
      if (lastSent == today) return; // already sent today

      final data = await BriefingService().fetchBriefing();

      final title = _buildBriefingTitle(data);
      final body = _buildBriefingBody(data);

      const androidDetails = AndroidNotificationDetails(
        _briefingChannelId,
        'Ранковий бріфінг',
        channelDescription: 'Щоденне зведення за ніч',
        importance: Importance.high,
        priority: Priority.high,
        icon: '@mipmap/ic_launcher',
      );
      const iosDetails = DarwinNotificationDetails(
        presentAlert: true,
        presentBadge: false,
        presentSound: true,
      );
      const details = NotificationDetails(
        android: androidDetails,
        iOS: iosDetails,
      );

      await plugin.show(_briefingNotifId, title, body, details,
          payload: 'briefing');
      await prefs.setString(_briefingDateKey, today);
      appDebugLog('BriefingService: morning briefing sent');
    } catch (e) {
      appDebugLog('BriefingService scheduleNotifications error: $e');
    }
  }

  static String _buildBriefingTitle(BriefingData data) {
    if (data.userRegionAlarmCount > 0 && data.userRegionName != null) {
      return '☀️ Ранок. Ваш регіон: ${data.userRegionAlarmCount} '
          '${_alarmWord(data.userRegionAlarmCount)}';
    }
    if (data.totalAlarmsToday > 0) {
      return '☀️ Ранковий бріфінг';
    }
    return '☀️ Спокійна ніч';
  }

  static String _buildBriefingBody(BriefingData data) {
    final parts = <String>[];

    if (data.totalThreats > 0) {
      final threats = <String>[];
      if (data.drones > 0) threats.add('${data.drones} дрон${_wordEnd(data.drones, '', 'и', 'ів')}');
      if (data.missiles > 0) threats.add('${data.missiles} ракет${_wordEnd(data.missiles, 'а', 'и', '')}');
      if (data.kab > 0) threats.add('${data.kab} КАБ');
      if (data.ballistic > 0) threats.add('${data.ballistic} балістик${_wordEnd(data.ballistic, 'а', 'и', '')}');
      if (threats.isNotEmpty) parts.add('Загрози: ${threats.join(', ')}');
    }

    if (data.totalAlarmsToday > 0) {
      parts.add('Тривог по Україні: ${data.totalAlarmsToday}');
    }

    if (parts.isEmpty) {
      return 'Вночі все було тихо. Зараз спокійно.';
    }
    return parts.join(' · ');
  }

  static String _alarmWord(int n) {
    if (n == 1) return 'тривога';
    if (n >= 2 && n <= 4) return 'тривоги';
    return 'тривог';
  }

  static String _wordEnd(int n, String one, String few, String many) {
    final mod10 = n % 10;
    final mod100 = n % 100;
    if (mod100 >= 11 && mod100 <= 19) return many;
    if (mod10 == 1) return one;
    if (mod10 >= 2 && mod10 <= 4) return few;
    return many;
  }
}


class BriefingData {
  final bool isMorning;
  final int totalAlarmsToday;
  final List<String> alarmRegions;
  final int drones;
  final int missiles;
  final int kab;
  final int ballistic;
  final String? userRegionName;
  final int userRegionAlarmCount;
  final int userRegionsTotal;
  final bool fromCache;

  BriefingData({
    required this.isMorning,
    required this.totalAlarmsToday,
    required this.alarmRegions,
    required this.drones,
    required this.missiles,
    required this.kab,
    required this.ballistic,
    this.userRegionName,
    this.userRegionAlarmCount = 0,
    this.userRegionsTotal = 0,
    this.fromCache = false,
  });

  bool get hasMultipleRegions => userRegionsTotal > 1;

  int get totalThreats => drones + missiles + kab + ballistic;

  Map<String, dynamic> toJson() => {
    'isMorning': isMorning,
    'totalAlarmsToday': totalAlarmsToday,
    'alarmRegions': alarmRegions,
    'drones': drones,
    'missiles': missiles,
    'kab': kab,
    'ballistic': ballistic,
    'userRegionName': userRegionName,
    'userRegionAlarmCount': userRegionAlarmCount,
    'userRegionsTotal': userRegionsTotal,
  };

  static BriefingData fromJson(Map<String, dynamic> json) {
    final regs = json['alarmRegions'];
    return BriefingData(
      isMorning: json['isMorning'] as bool? ?? true,
      totalAlarmsToday: json['totalAlarmsToday'] as int? ?? 0,
      alarmRegions: regs is List ? regs.map((e) => e.toString()).toList() : [],
      drones: json['drones'] as int? ?? 0,
      missiles: json['missiles'] as int? ?? 0,
      kab: json['kab'] as int? ?? 0,
      ballistic: json['ballistic'] as int? ?? 0,
      userRegionName: json['userRegionName'] as String?,
      userRegionAlarmCount: json['userRegionAlarmCount'] as int? ?? 0,
      userRegionsTotal: json['userRegionsTotal'] as int? ?? 0,
      fromCache: true,
    );
  }
}
