import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../models/map_models.dart';
import 'package:neptun_alarm_app/config/api_config.dart';
import 'package:neptun_alarm_app/core/network/http_retry.dart';
import 'map_offline_cache.dart';

dynamic _decodeJson(String body) => json.decode(body);

class MapAlarmData {
  final Map<String, bool> stateAlarms;
  final Map<String, bool> districtAlarms;
  final Map<String, String> stateThreatTypes;
  final int stateCount;
  final int districtCount;
  final Set<String> ballisticRegions;

  MapAlarmData({
    required this.stateAlarms,
    required this.districtAlarms,
    required this.stateThreatTypes,
    required this.stateCount,
    required this.districtCount,
    required this.ballisticRegions,
  });
}

class MapMarkerData {
  final List<ThreatMarker> markers;
  final Map<String, int> counts;
  final bool? ballisticActive;
  final String? ballisticRegion;

  MapMarkerData({
    required this.markers,
    required this.counts,
    this.ballisticActive,
    this.ballisticRegion,
  });
}

class MapDataService {
  final http.Client _client;
  bool _isClosed = false;

  // ETag caching — avoid re-parsing identical responses
  String? _alarmsETag;
  MapAlarmData? _cachedAlarms;
  String? _markersETag;
  MapMarkerData? _cachedMarkers;

  MapDataService({http.Client? client}) : _client = client ?? http.Client();

  Future<MapAlarmData> fetchAlarms() async {
    try {
      if (_isClosed) return _cachedAlarms ?? _emptyAlarmData();
      final headers = <String, String>{};
      if (_alarmsETag != null) {
        headers['If-None-Match'] = _alarmsETag!;
      }
      final response = await httpGetWithRetries(
        _client,
        Uri.parse(ApiConfig.alarmsAll),
        headers: headers,
        timeout: const Duration(seconds: 8),
      );

      // 304 Not Modified — return cached data
      if (response.statusCode == 304 && _cachedAlarms != null) {
        return _cachedAlarms!;
      }

      if (response.statusCode != 200) {
        debugPrint('fetchAlarms: HTTP ${response.statusCode}');
        return _cachedAlarms ?? _emptyAlarmData();
      }

      // Save ETag for next request
      final etag = response.headers['etag'];
      if (etag != null) _alarmsETag = etag;

      final data = await compute(_decodeJson, response.body);

      final Map<String, bool> newStateAlarms = {};
      final Map<String, bool> newDistrictAlarms = {};
      final Map<String, String> newStateThreatTypes = {};
      final Set<String> currentBallisticRegions = {};
      int stateCount = 0;
      int districtCount = 0;

      const regionNames = <String, String>{
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

      if (data is List) {
        for (final region in data) {
          final regionId = region['regionId']?.toString();
          final regionType = region['regionType'] ?? '';
          final activeAlerts = region['activeAlerts'] as List? ?? [];
          final regionName =
              region['regionName']?.toString() ?? regionNames[regionId] ?? '';

          if (regionId == null) continue;

          final hasAlarm = activeAlerts.isNotEmpty;

          if (regionType == 'State') {
            newStateAlarms[regionId] = hasAlarm;
            if (hasAlarm) {
              stateCount++;
              for (final alert in activeAlerts) {
                final alertType = alert['type']?.toString() ?? '';
                if (alertType == 'DRONES' || alertType.contains('DRONE')) {
                  newStateThreatTypes[regionId] = ThreatType.shahed;
                } else if (alertType == 'BALLISTIC' ||
                    alertType == 'MISSILE' ||
                    alertType.contains('BALLISTIC')) {
                  newStateThreatTypes[regionId] = ThreatType.raketa;
                  currentBallisticRegions.add(
                    regionName.isNotEmpty ? regionName : regionId,
                  );
                } else if (alertType == 'AIR') {
                  newStateThreatTypes[regionId] = ThreatType.avia;
                }
              }
            }
          } else if (regionType == 'District') {
            newDistrictAlarms[regionId] = hasAlarm;
            if (hasAlarm) {
              districtCount++;
              for (final alert in activeAlerts) {
                final alertType = alert['type']?.toString() ?? '';
                if (alertType == 'BALLISTIC' ||
                    alertType == 'MISSILE' ||
                    alertType.contains('BALLISTIC')) {
                  currentBallisticRegions.add(
                    regionName.isNotEmpty ? regionName : regionId,
                  );
                }
              }
            }
          }
        }
      } else if (data is Map) {
        data.forEach((key, value) {
          final regionId = key.toString();
          bool hasAlarm = false;

          if (value is bool) {
            hasAlarm = value;
          } else if (value is Map && value.containsKey('alarm')) {
            hasAlarm = value['alarm'] == true;
          }

          newStateAlarms[regionId] = hasAlarm;
          if (hasAlarm) stateCount++;
        });
      }

      final result = MapAlarmData(
        stateAlarms: newStateAlarms,
        districtAlarms: newDistrictAlarms,
        stateThreatTypes: newStateThreatTypes,
        stateCount: stateCount,
        districtCount: districtCount,
        ballisticRegions: currentBallisticRegions,
      );
      _cachedAlarms = result;
      MapOfflineCache.instance.saveAlarms(result);
      return result;
    } catch (e) {
      debugPrint('fetchAlarms error: $e');
      final cached = await MapOfflineCache.instance.loadAlarms();
      return cached ?? _cachedAlarms ?? _emptyAlarmData();
    }
  }

  static MapAlarmData _emptyAlarmData() => MapAlarmData(
    stateAlarms: {},
    districtAlarms: {},
    stateThreatTypes: {},
    stateCount: 0,
    districtCount: 0,
    ballisticRegions: {},
  );

  Future<MapMarkerData> fetchThreatMarkers({required int timeRange}) async {
    try {
      if (_isClosed) return _cachedMarkers ?? _emptyMarkerData();
      final headers = <String, String>{};
      if (_markersETag != null) {
        headers['If-None-Match'] = _markersETag!;
      }
      final response = await httpGetWithRetries(
        _client,
        Uri.parse('${ApiConfig.data}?timeRange=$timeRange'),
        headers: headers,
        timeout: const Duration(seconds: 8),
      );

      // 304 Not Modified — return cached data
      if (response.statusCode == 304 && _cachedMarkers != null) {
        return _cachedMarkers!;
      }

      if (response.statusCode != 200) {
        debugPrint('fetchThreatMarkers: HTTP ${response.statusCode}');
        return _cachedMarkers ?? _emptyMarkerData();
      }

      // Save ETag for next request
      final etag = response.headers['etag'];
      if (etag != null) _markersETag = etag;

      final data = await compute(_decodeJson, response.body);

      final List<ThreatMarker> newMarkers = [];
      final Map<String, int> newCounts = {};

      bool? ballisticActive;
      String? ballisticRegion;

      if (data is Map && data['ballistic_threat'] != null) {
        final ballisticThreat = data['ballistic_threat'];
        ballisticActive = ballisticThreat['active'] == true;
        ballisticRegion = ballisticThreat['region'] as String?;
      }

      List? markersData;
      if (data is Map) {
        markersData = data['tracks'] ?? data['items'] ?? [];
      } else if (data is List) {
        markersData = data;
      }

      if (markersData != null) {
        for (final item in markersData) {
          if (item is! Map) continue;

          final lat = double.tryParse(item['lat']?.toString() ?? '');
          final lng = double.tryParse(item['lng']?.toString() ?? '');

          if (lat == null || lng == null) continue;
          if (!MapBounds.isInBounds(lat, lng)) continue;

          final itemMap = Map<String, dynamic>.from(item);
          final marker = ThreatMarker.fromJson(itemMap);
          newMarkers.add(marker);
          newCounts[marker.threatType] =
              (newCounts[marker.threatType] ?? 0) + 1;
        }
      }

      final result = MapMarkerData(
        markers: newMarkers,
        counts: newCounts,
        ballisticActive: ballisticActive,
        ballisticRegion: ballisticRegion,
      );
      _cachedMarkers = result;
      MapOfflineCache.instance.saveMarkers(result);
      return result;
    } catch (e) {
      debugPrint('fetchThreatMarkers error: $e');
      final cached = await MapOfflineCache.instance.loadMarkers();
      return cached ?? _cachedMarkers ?? _emptyMarkerData();
    }
  }

  static MapMarkerData _emptyMarkerData() => MapMarkerData(
    markers: [],
    counts: {},
    ballisticActive: null,
    ballisticRegion: null,
  );

  void dispose() {
    if (_isClosed) return;
    _client.close();
    _isClosed = true;
  }
}
