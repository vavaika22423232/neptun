import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../domain/radar_snapshot.dart';

/// Локальний кеш останнього знімка Радару для offline / stale UI.
class RadarSnapshotCache {
  static const _prefsKey = 'radar_snapshot_cache_v1';

  Future<void> save(RadarSnapshot snapshot) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
      _prefsKey,
      jsonEncode({
        'markers': snapshot.markers,
        'activeOblastsUnderAlarm': snapshot.activeOblastsUnderAlarm,
        'fetchedAt': snapshot.fetchedAt.toIso8601String(),
      }),
    );
  }

  Future<RadarSnapshot?> load() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_prefsKey);
    if (raw == null || raw.isEmpty) return null;
    try {
      final map = jsonDecode(raw) as Map<String, dynamic>;
      final markersRaw = map['markers'];
      final markers = markersRaw is List
          ? markersRaw
              .whereType<Map>()
              .map((e) => Map<String, dynamic>.from(e))
              .toList()
          : <Map<String, dynamic>>[];
      final fetchedAt = DateTime.tryParse(map['fetchedAt']?.toString() ?? '') ??
          DateTime.fromMillisecondsSinceEpoch(0);
      return RadarSnapshot(
        markers: markers,
        activeOblastsUnderAlarm:
            (map['activeOblastsUnderAlarm'] as num?)?.toInt() ?? 0,
        fetchedAt: fetchedAt,
        fromDiskCache: true,
      );
    } catch (_) {
      return null;
    }
  }
}
