import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:path_provider/path_provider.dart';
import 'dart:io';
import 'map_data_service.dart';
import '../models/map_models.dart';

/// Зберігає останні дані тривог та маркерів для офлайн-режиму.
/// При відсутності мережі показує кешовані дані.
class MapOfflineCache {
  MapOfflineCache._();
  static final MapOfflineCache _instance = MapOfflineCache._();
  static MapOfflineCache get instance => _instance;

  static const _alarmsKey = 'map_offline_alarms';
  static const _markersKey = 'map_offline_markers';
  static const _alarmsTsKey = 'map_offline_alarms_ts';
  static const _markersTsKey = 'map_offline_markers_ts';
  static const _maxAgeHours = 24; // Не показувати кеш старіший ніж 24 год

  String? _cacheDir;

  Future<String> _getCacheDir() async {
    if (_cacheDir != null) return _cacheDir!;
    final dir = await getApplicationDocumentsDirectory();
    _cacheDir = dir.path;
    return _cacheDir!;
  }

  Future<void> saveAlarms(MapAlarmData data) async {
    try {
      final obj = {
        'stateAlarms': data.stateAlarms,
        'districtAlarms': data.districtAlarms,
        'stateThreatTypes': data.stateThreatTypes,
        'stateCount': data.stateCount,
        'districtCount': data.districtCount,
        'ballisticRegions': data.ballisticRegions.toList(),
      };
      final json = jsonEncode(obj);
      final file = File('${await _getCacheDir()}/$_alarmsKey.json');
      await file.writeAsString(json);
      final tsFile = File('${await _getCacheDir()}/$_alarmsTsKey');
      await tsFile.writeAsString(
        DateTime.now().millisecondsSinceEpoch.toString(),
      );
    } catch (e) {
      debugPrint('MapOfflineCache saveAlarms: $e');
    }
  }

  Future<void> saveMarkers(MapMarkerData data) async {
    try {
      final markersJson = data.markers.map((m) => m.toJson()).toList();
      final obj = {
        'markers': markersJson,
        'counts': data.counts,
        'ballisticActive': data.ballisticActive,
        'ballisticRegion': data.ballisticRegion,
      };
      final json = jsonEncode(obj);
      final file = File('${await _getCacheDir()}/$_markersKey.json');
      await file.writeAsString(json);
      final tsFile = File('${await _getCacheDir()}/$_markersTsKey');
      await tsFile.writeAsString(
        DateTime.now().millisecondsSinceEpoch.toString(),
      );
    } catch (e) {
      debugPrint('MapOfflineCache saveMarkers: $e');
    }
  }

  bool _isStale(int? tsMs) {
    if (tsMs == null) return true;
    final age = DateTime.now().millisecondsSinceEpoch - tsMs;
    return age > _maxAgeHours * 60 * 60 * 1000;
  }

  Future<MapAlarmData?> loadAlarms() async {
    try {
      final tsFile = File('${await _getCacheDir()}/$_alarmsTsKey');
      if (!await tsFile.exists()) return null;
      final tsMs = int.tryParse(await tsFile.readAsString());
      if (_isStale(tsMs)) return null;

      final file = File('${await _getCacheDir()}/$_alarmsKey.json');
      if (!await file.exists()) return null;
      final data = jsonDecode(await file.readAsString()) as Map;
      return MapAlarmData(
        stateAlarms: Map<String, bool>.from(data['stateAlarms'] ?? {}),
        districtAlarms: Map<String, bool>.from(data['districtAlarms'] ?? {}),
        stateThreatTypes: Map<String, String>.from(data['stateThreatTypes'] ?? {}),
        stateCount: data['stateCount'] as int? ?? 0,
        districtCount: data['districtCount'] as int? ?? 0,
        ballisticRegions: Set<String>.from(data['ballisticRegions'] ?? []),
      );
    } catch (e) {
      debugPrint('MapOfflineCache loadAlarms: $e');
      return null;
    }
  }

  Future<MapMarkerData?> loadMarkers() async {
    try {
      final tsFile = File('${await _getCacheDir()}/$_markersTsKey');
      if (!await tsFile.exists()) return null;
      final tsMs = int.tryParse(await tsFile.readAsString());
      if (_isStale(tsMs)) return null;

      final file = File('${await _getCacheDir()}/$_markersKey.json');
      if (!await file.exists()) return null;
      final data = jsonDecode(await file.readAsString()) as Map;
      final markersList = data['markers'] as List? ?? [];
      final markers = markersList
          .map((e) => ThreatMarker.fromJson(Map<String, dynamic>.from(e as Map)))
          .toList();
      final counts = Map<String, int>.from(data['counts'] ?? {});
      return MapMarkerData(
        markers: markers,
        counts: counts,
        ballisticActive: data['ballisticActive'] as bool?,
        ballisticRegion: data['ballisticRegion'] as String?,
      );
    } catch (e) {
      debugPrint('MapOfflineCache loadMarkers: $e');
      return null;
    }
  }

  Future<DateTime?> lastAlarmsUpdate() async {
    try {
      final tsFile = File('${await _getCacheDir()}/$_alarmsTsKey');
      if (!await tsFile.exists()) return null;
      final tsMs = int.tryParse(await tsFile.readAsString());
      if (tsMs == null) return null;
      return DateTime.fromMillisecondsSinceEpoch(tsMs);
    } catch (_) {
      return null;
    }
  }
}
