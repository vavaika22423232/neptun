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
  /// Повітряна куля / аеростат (не БПЛА)
  static const String airBalloon = 'air_balloon';

  static const Map<String, String> names = {
    shahed: '🛩️ Шахеди/БПЛА',
    airBalloon: '🎈 Повітряна куля',
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

  static const Map<String, IconData> icons = {
    shahed: Icons.flight,
    airBalloon: Icons.cloud_outlined,
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
      case airBalloon:
        return const Color(0xFF4FC3F7);
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

// ===== МАРКЕР ЗАГРОЗИ =====
/// Поля JSON узгоджені з Next.js `Marker` (`nextjs-app/src/types/index.ts`) та відповіддю `/api/data`.
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
  /// Сервер: `marker_icon` (файл іконки, напр. fpvdrone.png).
  final String? markerIcon;
  /// Прозорість іконки на карті (0–1).
  final double mapVisualOpacity;
  final double? courseBearing;
  final double? tickerBearing;
  final String? courseDirection;
  final String? arrowDirection;
  final String? trackState;
  final double? trackConfidence;
  final String? motionReason;
  final int? lastObservationEpoch;
  final String? geoDecisionReason;
  final String? geocodeSource;

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
    this.markerIcon,
    this.mapVisualOpacity = 1.0,
    this.courseBearing,
    this.tickerBearing,
    this.courseDirection,
    this.arrowDirection,
    this.trackState,
    this.trackConfidence,
    this.motionReason,
    this.lastObservationEpoch,
    this.geoDecisionReason,
    this.geocodeSource,
  });

  factory ThreatMarker.fromJson(Map<String, dynamic> json) {
    // Парсимо стару траєкторію якщо є
    List<TrajectoryPoint>? path;
    if (json['projected_path'] != null && json['projected_path'] is List) {
      path = (json['projected_path'] as List)
          .map((p) => TrajectoryPoint.fromJson(p))
          .toList();
    }

    // Парсимо нову AI траєкторію якщо є
    AITrajectory? aiTrajectory;
    if (json['trajectory'] != null && json['trajectory'] is Map) {
      aiTrajectory = AITrajectory.fromJson(json['trajectory']);
    }

    final countRaw = json['count'];
    final count = countRaw is int
        ? countRaw
        : (countRaw != null ? int.tryParse(countRaw.toString()) : null);

    final markerIconRaw = json['marker_icon']?.toString();
    final markerIcon =
        (markerIconRaw != null && markerIconRaw.trim().isNotEmpty)
            ? markerIconRaw.trim()
            : null;

    double parseOp(dynamic v) {
      if (v == null) return 1.0;
      final x = double.tryParse(v.toString());
      if (x == null || !x.isFinite) return 1.0;
      return x.clamp(0.0, 1.0);
    }

    double? parseBearing(dynamic v) {
      if (v == null) return null;
      final x = double.tryParse(v.toString());
      if (x == null || !x.isFinite) return null;
      return x;
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
      markerIcon: markerIcon,
      mapVisualOpacity: parseOp(
        json['map_visual_opacity'] ?? json['mapVisualOpacity'],
      ),
      courseBearing: parseBearing(json['course_bearing']),
      tickerBearing: parseBearing(json['ticker_bearing']),
      courseDirection: json['course_direction']?.toString(),
      arrowDirection: json['arrow_direction']?.toString(),
      trackState: json['track_state']?.toString(),
      trackConfidence: double.tryParse(json['track_confidence']?.toString() ?? ''),
      motionReason: json['motion_reason']?.toString(),
      lastObservationEpoch: int.tryParse(json['last_observation_epoch']?.toString() ?? ''),
      geoDecisionReason: json['geo_decision_reason']?.toString(),
      geocodeSource: json['geocode_source']?.toString(),
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
      if (markerIcon != null) 'marker_icon': markerIcon,
      'map_visual_opacity': mapVisualOpacity,
      if (courseBearing != null) 'course_bearing': courseBearing,
      if (tickerBearing != null) 'ticker_bearing': tickerBearing,
      if (courseDirection != null) 'course_direction': courseDirection,
      if (arrowDirection != null) 'arrow_direction': arrowDirection,
      if (trackState != null) 'track_state': trackState,
      if (trackConfidence != null) 'track_confidence': trackConfidence,
      if (motionReason != null) 'motion_reason': motionReason,
      if (lastObservationEpoch != null) 'last_observation_epoch': lastObservationEpoch,
      if (geoDecisionReason != null) 'geo_decision_reason': geoDecisionReason,
      if (geocodeSource != null) 'geocode_source': geocodeSource,
    };
  }

  bool get hasTrajectory =>
      (projectedPath != null && projectedPath!.length > 1) ||
      (trajectory != null && trajectory!.isValid);

  bool get hasAITrajectory => trajectory != null && trajectory!.isValid;

  /// Apply partial update from SSE (track_update/marker_update). Returns new instance.
  ThreatMarker applyPartialUpdate(Map<String, dynamic> updates) {
    final json = toJson();
    for (final e in updates.entries) {
      if (e.key != 'id') json[e.key] = e.value;
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
