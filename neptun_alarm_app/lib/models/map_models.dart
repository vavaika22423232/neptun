import 'package:flutter/material.dart';

// ===== ТИПИ ЗАГРОЗ (маркери) =====
class ThreatType {
  static const String shahed = 'shahed';
  static const String raketa = 'raketa';
  static const String avia = 'avia';
  static const String artillery = 'artillery';
  static const String obstril = 'obstril';
  static const String fpv = 'fpv';
  static const String pusk = 'pusk';
  static const String kab = 'kab';
  static const String rszv = 'rszv';
  static const String rozved = 'rozved';
  static const String vibuh = 'vibuh';
  static const String alarm = 'alarm';
  static const String alarmCancel = 'alarm_cancel';

  static const Map<String, String> names = {
    shahed: '🛩️ Шахеди/БПЛА',
    raketa: '🚀 Ракети',
    avia: '✈️ Авіація',
    artillery: '💥 Артилерія',
    obstril: '💥 Обстріл',
    fpv: '🎯 FPV дрони',
    pusk: '🚀 Пуски',
    kab: '💣 КАБи',
    rszv: '💣 РСЗВ',
    rozved: '🔍 Розвідники',
    vibuh: '💥 Вибухи',
    alarm: '🚨 Тривога',
    alarmCancel: '✅ Відбій',
  };

  static const Map<String, String> emojis = {
    shahed: '🛩️',
    raketa: '🚀',
    avia: '✈️',
    artillery: '💥',
    obstril: '💥',
    fpv: '🎯',
    pusk: '🚀',
    kab: '💣',
    rszv: '💣',
    rozved: '🔍',
    vibuh: '💥',
    alarm: '🚨',
    alarmCancel: '✅',
  };

  static const Map<String, IconData> icons = {
    shahed: Icons.flight,
    raketa: Icons.rocket_launch,
    avia: Icons.airplanemode_active,
    artillery: Icons.local_fire_department,
    obstril: Icons.local_fire_department,
    fpv: Icons.sports_esports,
    pusk: Icons.rocket,
    kab: Icons.dangerous,
    rszv: Icons.whatshot,
    rozved: Icons.visibility,
    vibuh: Icons.warning,
    alarm: Icons.notifications_active,
    alarmCancel: Icons.check_circle,
  };

  static Color getColor(String type) {
    switch (type) {
      case shahed:
      case fpv:
      case rozved:
        return Colors.orange;
      case raketa:
      case pusk:
      case kab:
      case rszv:
        return Colors.red;
      case avia:
        return Colors.purple;
      case artillery:
      case obstril:
      case vibuh:
        return Colors.amber;
      case alarm:
        return Colors.red;
      case alarmCancel:
        return Colors.green;
      default:
        return Colors.white;
    }
  }
}

// ===== ТОЧКА ТРАЄКТОРІЇ =====
class TrajectoryPoint {
  final double lat;
  final double lng;
  final double etaMinutes;
  final double fraction;

  TrajectoryPoint({
    required this.lat,
    required this.lng,
    required this.etaMinutes,
    required this.fraction,
  });

  factory TrajectoryPoint.fromJson(Map<String, dynamic> json) {
    return TrajectoryPoint(
      lat: double.tryParse(json['lat']?.toString() ?? '0') ?? 0,
      lng: double.tryParse(json['lng']?.toString() ?? '0') ?? 0,
      etaMinutes: double.tryParse(json['eta_minutes']?.toString() ?? '0') ?? 0,
      fraction: double.tryParse(json['fraction']?.toString() ?? '0') ?? 0,
    );
  }

  Map<String, dynamic> toJson() => {
        'lat': lat,
        'lng': lng,
        'eta_minutes': etaMinutes,
        'fraction': fraction,
      };
}

// ===== AI TRAJECTORY (новий формат з сервера) =====
class AITrajectory {
  final double startLat;
  final double startLng;
  final double endLat;
  final double endLng;
  final String sourceName;
  final String targetName;
  final bool predicted;

  AITrajectory({
    required this.startLat,
    required this.startLng,
    required this.endLat,
    required this.endLng,
    required this.sourceName,
    required this.targetName,
    this.predicted = false,
  });

  factory AITrajectory.fromJson(Map<String, dynamic> json) {
    final start = json['start'] as List?;
    final end = json['end'] as List?;
    return AITrajectory(
      startLat: (start?[0] as num?)?.toDouble() ?? 0,
      startLng: (start?[1] as num?)?.toDouble() ?? 0,
      endLat: (end?[0] as num?)?.toDouble() ?? 0,
      endLng: (end?[1] as num?)?.toDouble() ?? 0,
      sourceName: json['source_name'] ?? '',
      targetName: json['target_name'] ?? '',
      predicted: json['predicted'] == true,
    );
  }

  bool get isValid {
    // Trajectory is valid if start and end are different (at least 0.01 degree apart)
    return (startLat - endLat).abs() > 0.01 || (startLng - endLng).abs() > 0.01;
  }

  Map<String, dynamic> toJson() => {
        'start': [startLat, startLng],
        'end': [endLat, endLng],
        'source_name': sourceName,
        'target_name': targetName,
        'predicted': predicted,
      };
}

/// Точка треку з API (`positions`): для курсу по останніх спостереженнях.
class ThreatTrackPoint {
  final double lat;
  final double lng;
  /// Unix ms (або сек — нормалізуйте на клієнті SSE)
  final int ts;

  const ThreatTrackPoint({
    required this.lat,
    required this.lng,
    required this.ts,
  });

  factory ThreatTrackPoint.fromJson(Map<String, dynamic> json) {
    final tsRaw = json['ts'];
    int ts;
    if (tsRaw is int) {
      ts = tsRaw;
    } else if (tsRaw is num) {
      ts = tsRaw.toInt();
    } else {
      ts = int.tryParse(tsRaw?.toString() ?? '') ?? 0;
    }
    if (ts > 0 && ts < 20000000000) {
      ts *= 1000;
    }
    return ThreatTrackPoint(
      lat: double.tryParse(json['lat']?.toString() ?? '0') ?? 0,
      lng: double.tryParse(json['lng']?.toString() ?? '0') ?? 0,
      ts: ts,
    );
  }

  Map<String, dynamic> toJson() => {'lat': lat, 'lng': lng, 'ts': ts};
}

// ===== МАРКЕР ЗАГРОЗИ =====
class ThreatMarker {
  final String? id;
  final String? trackId; // For matching track_update events
  final double lat;
  final double lng;
  final String threatType;
  final String place;
  final String text;
  final String date;
  final List<TrajectoryPoint>? projectedPath; // Для старих траєкторій
  final AITrajectory? trajectory; // Для AI траєкторій
  final double? etaMinutes;
  final double? distanceKm;
  final int? count; // Кількість БПЛА/шахедів (5 штук, 5х)
  /// 0–100 з API (`confidence_0_100`); може бути null у старих кешах
  final int? confidence0_100;
  /// `point` | `approximate` | `predictive` | … з worker
  final String? placementMode;
  final double? confidence;
  /// Курс 0–360 з worker / GPT
  final double? courseBearing;
  final double? tickerBearing;
  final String? courseDirection;
  final String? arrowDirection;
  /// Історія позицій (як на веб)
  final List<ThreatTrackPoint>? positions;
  /// Ім'я файла з API (`marker_icon`), напр. fpvdrone.png — має пріоритет над threatType для іконки
  final String? markerIcon;

  ThreatMarker({
    this.id,
    this.trackId,
    required this.lat,
    required this.lng,
    required this.threatType,
    this.place = '',
    this.text = '',
    this.date = '',
    this.projectedPath,
    this.trajectory,
    this.etaMinutes,
    this.distanceKm,
    this.count,
    this.confidence0_100,
    this.placementMode,
    this.confidence,
    this.courseBearing,
    this.tickerBearing,
    this.courseDirection,
    this.arrowDirection,
    this.positions,
    this.markerIcon,
  });

  factory ThreatMarker.fromJson(Map<String, dynamic> json) {
    // Парсимо стару траєкторію якщо є
    List<TrajectoryPoint>? path;
    if (json['projected_path'] != null && json['projected_path'] is List) {
      path = (json['projected_path'] as List)
          .whereType<Map>()
          .map(
            (p) => TrajectoryPoint.fromJson(Map<String, dynamic>.from(p)),
          )
          .toList();
    }

    // Парсимо нову AI траєкторію якщо є
    AITrajectory? aiTrajectory;
    if (json['trajectory'] != null && json['trajectory'] is Map) {
      aiTrajectory = AITrajectory.fromJson(
        Map<String, dynamic>.from(json['trajectory']! as Map),
      );
    }

    final countRaw = json['count'];
    final count = countRaw is int
        ? countRaw
        : (countRaw != null ? int.tryParse(countRaw.toString()) : null);

    final c100Raw = json['confidence_0_100'];
    int? c100;
    if (c100Raw is int) {
      c100 = c100Raw;
    } else if (c100Raw != null) {
      c100 = int.tryParse(c100Raw.toString());
    }

    List<ThreatTrackPoint>? posList;
    if (json['positions'] is List) {
      posList = (json['positions'] as List)
          .whereType<Map>()
          .map((p) => ThreatTrackPoint.fromJson(Map<String, dynamic>.from(p)))
          .toList();
    }

    return ThreatMarker(
      id: json['id']?.toString(),
      trackId: json['track_id']?.toString(),
      lat: double.tryParse(json['lat']?.toString() ?? '0') ?? 0,
      lng: double.tryParse(json['lng']?.toString() ?? '0') ?? 0,
      threatType: json['threat_type'] ?? 'default',
      place: json['place'] ?? '',
      text: json['text'] ?? '',
      date: json['date'] ?? '',
      projectedPath: path,
      trajectory: aiTrajectory,
      etaMinutes: double.tryParse(json['eta_minutes']?.toString() ?? ''),
      distanceKm: double.tryParse(json['distance_km']?.toString() ?? ''),
      count: count,
      confidence0_100: c100,
      placementMode: json['placement_mode']?.toString(),
      confidence: double.tryParse(json['confidence']?.toString() ?? ''),
      courseBearing: double.tryParse(json['course_bearing']?.toString() ?? ''),
      tickerBearing: double.tryParse(json['ticker_bearing']?.toString() ?? ''),
      courseDirection: json['course_direction']?.toString(),
      arrowDirection: json['arrow_direction']?.toString(),
      positions: posList,
      markerIcon: json['marker_icon']?.toString(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      if (id != null) 'id': id,
      if (trackId != null) 'track_id': trackId,
      'lat': lat,
      'lng': lng,
      'threat_type': threatType,
      'place': place,
      'text': text,
      'date': date,
      if (projectedPath != null)
        'projected_path': projectedPath!.map((p) => p.toJson()).toList(),
      if (trajectory != null) 'trajectory': trajectory!.toJson(),
      if (etaMinutes != null) 'eta_minutes': etaMinutes,
      if (distanceKm != null) 'distance_km': distanceKm,
      if (count != null) 'count': count,
      if (confidence0_100 != null) 'confidence_0_100': confidence0_100,
      if (placementMode != null && placementMode!.isNotEmpty)
        'placement_mode': placementMode,
      if (confidence != null) 'confidence': confidence,
      if (courseBearing != null) 'course_bearing': courseBearing,
      if (tickerBearing != null) 'ticker_bearing': tickerBearing,
      if (courseDirection != null && courseDirection!.isNotEmpty)
        'course_direction': courseDirection,
      if (arrowDirection != null && arrowDirection!.isNotEmpty)
        'arrow_direction': arrowDirection,
      if (positions != null)
        'positions': positions!.map((p) => p.toJson()).toList(),
      if (markerIcon != null && markerIcon!.isNotEmpty) 'marker_icon': markerIcon,
    };
  }

  /// Opacity for map icon (approximate / predictive / low score → dimmer).
  double get mapVisualOpacity {
    var base = 1.0;
    final pm = (placementMode ?? '').toLowerCase();
    if (pm == 'approximate') {
      base = 0.62;
    } else if (pm == 'predictive') {
      base = 0.5;
    }
    final c100 = confidence0_100;
    if (c100 != null) {
      final c = (c100.clamp(0, 100)) / 100.0;
      if (c < 0.78) {
        base *= 0.55 + 0.45 * c;
      }
    } else if (confidence != null && confidence! < 0.78) {
      final c = confidence!.clamp(0.0, 1.0);
      base *= 0.55 + 0.45 * c;
    }
    return base.clamp(0.32, 1.0);
  }

  bool get hasTrajectory =>
      (projectedPath != null && projectedPath!.length > 1) ||
      (trajectory != null && trajectory!.isValid);

  bool get hasAITrajectory => trajectory != null && trajectory!.isValid;

  /// Apply partial update from SSE (track_update/marker_update). Returns new instance.
  ThreatMarker applyPartialUpdate(Map<String, dynamic> updates) {
    final json = Map<String, dynamic>.from(toJson());
    for (final e in updates.entries) {
      if (e.key == 'id') continue;
      final v = e.value;
      if (v is Map) {
        json[e.key] = Map<String, dynamic>.from(
          v.map((k, dynamic val) => MapEntry(k.toString(), val)),
        );
      } else if (v is List) {
        json[e.key] = v
            .map((dynamic item) {
              if (item is Map) {
                return Map<String, dynamic>.from(
                  item.map((k, dynamic val) => MapEntry(k.toString(), val)),
                );
              }
              return item;
            })
            .toList();
      } else {
        json[e.key] = v;
      }
    }
    return ThreatMarker.fromJson(json);
  }
}

// ===== MAP BOUNDS (Україна) =====
class MapBounds {
  static const double minLat = 44.2;
  static const double maxLat = 52.4;
  static const double minLng = 22.0;
  static const double maxLng = 40.2;

  static Offset latLngToPercent(double lat, double lng) {
    final x = (lng - minLng) / (maxLng - minLng);
    final y = (maxLat - lat) / (maxLat - minLat);
    return Offset(x.clamp(0.0, 1.0), y.clamp(0.0, 1.0));
  }

  static bool isInBounds(double lat, double lng) {
    return lat >= minLat && lat <= maxLat && lng >= minLng && lng <= maxLng;
  }
}

// ===== THREAT HISTORY ENTRY =====
class ThreatHistoryEntry {
  final DateTime timestamp;
  final Map<String, int> counts;

  ThreatHistoryEntry({required this.timestamp, required this.counts});

  int get total => counts.values.fold<int>(0, (sum, v) => sum + v);
}
