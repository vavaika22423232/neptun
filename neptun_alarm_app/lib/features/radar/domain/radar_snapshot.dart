import 'package:flutter/foundation.dart';

/// Іммутабельний знімок відповіді Радару (маркери + тривога по областях).
@immutable
class RadarSnapshot {
  const RadarSnapshot({
    required this.markers,
    required this.activeOblastsUnderAlarm,
    required this.fetchedAt,
  });

  /// Сирі маркери загроз із `GET /api/threats`.
  final List<Map<String, dynamic>> markers;

  /// Кількість областей з активним алармом за `GET /api/alarm-status`.
  final int activeOblastsUnderAlarm;

  final DateTime fetchedAt;
}
