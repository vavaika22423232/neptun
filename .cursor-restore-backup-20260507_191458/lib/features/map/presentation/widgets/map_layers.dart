import 'package:flutter/foundation.dart' show mapEquals;
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart' hide Path;

import '../../../../map/threat_bearing.dart';
import '../../../../models/map_models.dart';
import '../../../../services/threat_icon_manager.dart';
import '../../../../theme/map_colors.dart';

// ===== SVG MAP LAYER (for hybrid mode) =====
// This is a proper flutter_map layer that transforms with the map camera
// Draws STATIC base map (non-alarmed regions + static alarm color)
class SvgMapLayer extends StatelessWidget {
  final Map<String, List<Path>> statePathsCache;
  final Map<String, List<Path>> districtPathsCache;
  final Map<String, bool> stateAlarms;
  final Map<String, bool> districtAlarms;
  final Map<String, String> stateThreatTypes;
  final List<ThreatMarker> threatMarkers;
  final MapColors mapColors;
  final double opacity;
  final void Function(ThreatMarker) onMarkerTap;

  // SVG viewBox dimensions
  static const double svgWidth = 260.0;
  static const double svgHeight = 175.0;

  // Geographic bounds that SVG covers (must match MapBounds)
  static const double geoMinLat = 44.2;
  static const double geoMaxLat = 52.4;
  static const double geoMinLng = 22.0;
  static const double geoMaxLng = 40.2;

  const SvgMapLayer({
    super.key,
    required this.statePathsCache,
    required this.districtPathsCache,
    required this.stateAlarms,
    required this.districtAlarms,
    required this.stateThreatTypes,
    required this.threatMarkers,
    required this.mapColors,
    required this.opacity,
    required this.onMarkerTap,
  });

  /// Convert SVG coordinates to LatLng
  static LatLng svgToLatLng(double svgX, double svgY) {
    // SVG (0,0) = top-left = (geoMinLng, geoMaxLat)
    // SVG (svgWidth, svgHeight) = bottom-right = (geoMaxLng, geoMinLat)
    final lng = geoMinLng + (svgX / svgWidth) * (geoMaxLng - geoMinLng);
    final lat = geoMaxLat - (svgY / svgHeight) * (geoMaxLat - geoMinLat);
    return LatLng(lat, lng);
  }

  @override
  Widget build(BuildContext context) {
    final camera = MapCamera.of(context);

    // Pass opacity directly to painter — avoids expensive Opacity widget
    // which forces offscreen compositing (saveLayer) on entire CustomPaint
    return CustomPaint(
      size: Size.infinite,
      painter: SvgMapPainter(
        camera: camera,
        statePathsCache: statePathsCache,
        districtPathsCache: districtPathsCache,
        stateAlarms: stateAlarms,
        districtAlarms: districtAlarms,
        mapColors: mapColors,
        opacity: opacity,
      ),
    );
  }
}

// ===== SVG MAP PAINTER (static base — no pulse) =====
class SvgMapPainter extends CustomPainter {
  final MapCamera camera;
  final Map<String, List<Path>> statePathsCache;
  final Map<String, List<Path>> districtPathsCache;
  final Map<String, bool> stateAlarms;
  final Map<String, bool> districtAlarms;
  final MapColors mapColors;
  final double opacity;

  // Static cached Paint objects — avoid ~10 allocations per frame
  static final Paint _normalFill = Paint()..style = PaintingStyle.fill;
  static final Paint _alarmFill = Paint()..style = PaintingStyle.fill;
  static final Paint _normalStroke = Paint()
    ..style = PaintingStyle.stroke
    ..strokeJoin = StrokeJoin.round;
  static final Paint _alarmStroke = Paint()
    ..style = PaintingStyle.stroke
    ..strokeJoin = StrokeJoin.round;
  static final Paint _distAlarmFill = Paint()..style = PaintingStyle.fill;
  static final Paint _distAlarmStroke = Paint()..style = PaintingStyle.stroke;
  static final Paint _distBorder = Paint()..style = PaintingStyle.stroke;

  SvgMapPainter({
    required this.camera,
    required this.statePathsCache,
    required this.districtPathsCache,
    required this.stateAlarms,
    required this.districtAlarms,
    required this.mapColors,
    required this.opacity,
  });

  /// Convert SVG coordinates to screen offset using camera
  Offset svgToScreen(double svgX, double svgY) {
    final latLng = SvgMapLayer.svgToLatLng(svgX, svgY);
    return camera.latLngToScreenOffset(latLng);
  }

  /// Get canvas transformation to map SVG coordinates to screen
  void applyCanvasTransform(Canvas canvas) {
    final topLeft = svgToScreen(0, 0);
    final topRight = svgToScreen(SvgMapLayer.svgWidth, 0);
    final bottomLeft = svgToScreen(0, SvgMapLayer.svgHeight);
    final scaleX = (topRight.dx - topLeft.dx) / SvgMapLayer.svgWidth;
    final scaleY = (bottomLeft.dy - topLeft.dy) / SvgMapLayer.svgHeight;
    canvas.translate(topLeft.dx, topLeft.dy);
    canvas.scale(scaleX, scaleY);
  }

  /// Compute visible rect in SVG coordinates for viewport culling
  Rect _getVisibleSvgRect(Size size) {
    // Convert screen corners to SVG coordinates
    final svgW = SvgMapLayer.svgWidth;
    final svgH = SvgMapLayer.svgHeight;
    final topLeft = svgToScreen(0, 0);
    final topRight = svgToScreen(svgW, 0);
    final bottomLeft = svgToScreen(0, svgH);
    final scaleX = (topRight.dx - topLeft.dx) / svgW;
    final scaleY = (bottomLeft.dy - topLeft.dy) / svgH;
    if (scaleX == 0 || scaleY == 0) {
      return Rect.fromLTWH(0, 0, svgW, svgH); // Fallback: draw all
    }
    // Screen (0,0) → SVG coords
    final svgLeft = (0 - topLeft.dx) / scaleX;
    final svgTop = (0 - topLeft.dy) / scaleY;
    final svgRight = (size.width - topLeft.dx) / scaleX;
    final svgBottom = (size.height - topLeft.dy) / scaleY;
    // Add margin for strokes
    const margin = 5.0;
    return Rect.fromLTRB(
      svgLeft - margin,
      svgTop - margin,
      svgRight + margin,
      svgBottom + margin,
    );
  }

  @override
  void paint(Canvas canvas, Size size) {
    if (opacity <= 0) return; // fully transparent — skip entirely
    _paintPaths(canvas, size);
  }

  void _paintPaths(Canvas canvas, Size size) {
    // No full-screen background — the FlutterMap backgroundColor handles this

    canvas.save();
    applyCanvasTransform(canvas);

    final topLeft = svgToScreen(0, 0);
    final topRight = svgToScreen(SvgMapLayer.svgWidth, 0);
    final canvasScale = (topRight.dx - topLeft.dx) / SvgMapLayer.svgWidth;
    final strokeScale = (1.0 / canvasScale).clamp(0.3, 2.0);

    // Viewport culling rect in SVG coordinates
    final visibleRect = _getVisibleSvgRect(size);

    // === LAYER 1: STATES (static colors) ===
    // Update cached paint colors (mutate instead of allocating new Paint objects)
    _normalFill.color = mapColors.normalFill.withValues(alpha: opacity);
    final alarmColor = mapColors.isDark
        ? const Color(0xFF7f1d1d)
        : Color.fromRGBO(220, 38, 38, 0.7 * opacity);
    _alarmFill.color = alarmColor;
    _normalStroke
      ..color = mapColors.normalStroke.withValues(alpha: 0.5 * opacity)
      ..strokeWidth = 1.0 * strokeScale;
    _alarmStroke
      ..color = alarmColor
      ..strokeWidth = 1.2 * strokeScale;

    for (final entry in statePathsCache.entries) {
      final regionId = entry.key;
      final paths = entry.value;
      final hasAlarm = stateAlarms[regionId] ?? false;
      final fillPaint = hasAlarm ? _alarmFill : _normalFill;
      final strokePaint = hasAlarm ? _alarmStroke : _normalStroke;

      for (final svgPath in paths) {
        // Viewport culling: skip paths entirely outside visible area
        if (!svgPath.getBounds().overlaps(visibleRect)) continue;
        canvas.drawPath(svgPath, fillPaint);
        canvas.drawPath(svgPath, strokePaint);
      }
    }

    // === LAYER 2: DISTRICTS (alarmed only + borders at high zoom) ===
    final distAlarmColor = mapColors.isDark
        ? Color.fromRGBO(185, 28, 28, 0.7 * opacity)
        : Color.fromRGBO(239, 68, 68, 0.5 * opacity);
    _distAlarmFill.color = distAlarmColor;
    _distAlarmStroke
      ..color = distAlarmColor
      ..strokeWidth = 0.3 * strokeScale;

    for (final entry in districtPathsCache.entries) {
      final districtId = entry.key;
      final paths = entry.value;
      final hasAlarm = districtAlarms[districtId] ?? false;
      if (hasAlarm) {
        for (final svgPath in paths) {
          if (!svgPath.getBounds().overlaps(visibleRect)) continue;
          canvas.drawPath(svgPath, _distAlarmFill);
          canvas.drawPath(svgPath, _distAlarmStroke);
        }
      }
    }

    // District borders at higher zoom
    if (camera.zoom >= 7.5) {
      _distBorder
        ..color = mapColors.normalStroke.withValues(alpha: 0.08 * opacity)
        ..strokeWidth = 0.3 * strokeScale;
      for (final entry in districtPathsCache.entries) {
        final paths = entry.value;
        for (final svgPath in paths) {
          if (!svgPath.getBounds().overlaps(visibleRect)) continue;
          canvas.drawPath(svgPath, _distBorder);
        }
      }
    }

    canvas.restore();
  }

  @override
  bool shouldRepaint(SvgMapPainter oldDelegate) {
    // Reduced sensitivity: repaint less often during smooth zoom/pan
    if ((camera.zoom - oldDelegate.camera.zoom).abs() > 0.05) return true;
    if ((camera.center.latitude - oldDelegate.camera.center.latitude).abs() >
        0.001) {
      return true;
    }
    if ((camera.center.longitude - oldDelegate.camera.center.longitude).abs() >
        0.001) {
      return true;
    }
    if (opacity != oldDelegate.opacity) return true;
    if (mapColors.isDark != oldDelegate.mapColors.isDark) return true;
    if (stateAlarms.length != oldDelegate.stateAlarms.length) return true;
    if (districtAlarms.length != oldDelegate.districtAlarms.length) return true;
    if (!mapEquals(stateAlarms, oldDelegate.stateAlarms)) return true;
    if (!mapEquals(districtAlarms, oldDelegate.districtAlarms)) return true;
    return false;
  }
}

// ===== PULSE ALARM LAYER =====
// Separate layer that ONLY repaints alarmed regions with pulse animation.
// This avoids repainting all 125+ SVG paths on every animation tick.
class PulseAlarmLayer extends StatelessWidget {
  final Map<String, List<Path>> statePathsCache;
  final Map<String, List<Path>> districtPathsCache;
  final Map<String, bool> stateAlarms;
  final Map<String, bool> districtAlarms;
  final Animation<double> pulseAnimation;
  final MapColors mapColors;
  final double opacity;

  const PulseAlarmLayer({
    super.key,
    required this.statePathsCache,
    required this.districtPathsCache,
    required this.stateAlarms,
    required this.districtAlarms,
    required this.pulseAnimation,
    required this.mapColors,
    required this.opacity,
  });

  @override
  Widget build(BuildContext context) {
    final camera = MapCamera.of(context);

    // Only build this layer if there are active alarms
    final hasAlarms =
        stateAlarms.values.any((v) => v) || districtAlarms.values.any((v) => v);
    if (!hasAlarms) return const SizedBox.shrink();

    // Pass opacity directly to painter — avoids expensive Opacity saveLayer
    return AnimatedBuilder(
      animation: pulseAnimation,
      builder: (context, _) {
        return CustomPaint(
          size: Size.infinite,
          painter: PulseAlarmPainter(
            camera: camera,
            statePathsCache: statePathsCache,
            districtPathsCache: districtPathsCache,
            stateAlarms: stateAlarms,
            districtAlarms: districtAlarms,
            pulseValue: pulseAnimation.value,
            mapColors: mapColors,
            opacity: opacity,
          ),
        );
      },
    );
  }
}

// ===== PULSE ALARM PAINTER =====
// Only draws alarmed regions with animated pulse color.
// Typically redraws only 3-5 paths instead of 125+.
class PulseAlarmPainter extends CustomPainter {
  final MapCamera camera;
  final Map<String, List<Path>> statePathsCache;
  final Map<String, List<Path>> districtPathsCache;
  final Map<String, bool> stateAlarms;
  final Map<String, bool> districtAlarms;
  final double pulseValue;
  final MapColors mapColors;
  final double opacity;

  // Static cached paints
  static final Paint _pulseFill = Paint()..style = PaintingStyle.fill;
  static final Paint _pulseStroke = Paint()
    ..style = PaintingStyle.stroke
    ..strokeJoin = StrokeJoin.round;
  static final Paint _distPulseFill = Paint()..style = PaintingStyle.fill;
  static final Paint _distPulseStroke = Paint()..style = PaintingStyle.stroke;

  // Pre-computed lerp base colors
  static const _alarmBaseDark = Color(0xFF7f1d1d);
  static const _alarmHighDark = Color(0xFF991b1b);
  static const _distBaseDark = Color(0xFFB91C1C);
  static const _distHighDark = Color(0xFFDC2626);

  PulseAlarmPainter({
    required this.camera,
    required this.statePathsCache,
    required this.districtPathsCache,
    required this.stateAlarms,
    required this.districtAlarms,
    required this.pulseValue,
    required this.mapColors,
    required this.opacity,
  });

  Offset svgToScreen(double svgX, double svgY) {
    final latLng = SvgMapLayer.svgToLatLng(svgX, svgY);
    return camera.latLngToScreenOffset(latLng);
  }

  void applyCanvasTransform(Canvas canvas) {
    final topLeft = svgToScreen(0, 0);
    final topRight = svgToScreen(SvgMapLayer.svgWidth, 0);
    final bottomLeft = svgToScreen(0, SvgMapLayer.svgHeight);
    final scaleX = (topRight.dx - topLeft.dx) / SvgMapLayer.svgWidth;
    final scaleY = (bottomLeft.dy - topLeft.dy) / SvgMapLayer.svgHeight;
    canvas.translate(topLeft.dx, topLeft.dy);
    canvas.scale(scaleX, scaleY);
  }

  /// Compute visible rect in SVG coordinates for viewport culling
  Rect _getVisibleSvgRect(Size size) {
    final svgW = SvgMapLayer.svgWidth;
    final svgH = SvgMapLayer.svgHeight;
    final topLeft = svgToScreen(0, 0);
    final topRight = svgToScreen(svgW, 0);
    final bottomLeft = svgToScreen(0, svgH);
    final scaleX = (topRight.dx - topLeft.dx) / svgW;
    final scaleY = (bottomLeft.dy - topLeft.dy) / svgH;
    if (scaleX == 0 || scaleY == 0) {
      return Rect.fromLTWH(0, 0, svgW, svgH);
    }
    final svgLeft = (0 - topLeft.dx) / scaleX;
    final svgTop = (0 - topLeft.dy) / scaleY;
    final svgRight = (size.width - topLeft.dx) / scaleX;
    final svgBottom = (size.height - topLeft.dy) / scaleY;
    const margin = 5.0;
    return Rect.fromLTRB(
      svgLeft - margin,
      svgTop - margin,
      svgRight + margin,
      svgBottom + margin,
    );
  }

  @override
  void paint(Canvas canvas, Size size) {
    if (opacity <= 0) return; // fully transparent — skip entirely
    canvas.save();
    applyCanvasTransform(canvas);

    final topLeft = svgToScreen(0, 0);
    final topRight = svgToScreen(SvgMapLayer.svgWidth, 0);
    final canvasScale = (topRight.dx - topLeft.dx) / SvgMapLayer.svgWidth;
    final strokeScale = (1.0 / canvasScale).clamp(0.3, 2.0);

    // Viewport culling rect in SVG coordinates
    final visibleRect = _getVisibleSvgRect(size);

    // Animated alarm color for states — use pre-computed base colors
    final alarmColor = Color.lerp(
      mapColors.isDark ? _alarmBaseDark : Color.fromRGBO(220, 38, 38, 0.7),
      mapColors.isDark ? _alarmHighDark : Color.fromRGBO(248, 113, 113, 0.85),
      pulseValue,
    )!;

    _pulseFill.color = alarmColor.withValues(alpha: opacity);
    _pulseStroke
      ..color = alarmColor.withValues(alpha: opacity)
      ..strokeWidth = 1.2 * strokeScale;

    // Only draw alarmed states (typically 3-5 out of 25) — with viewport culling
    for (final entry in statePathsCache.entries) {
      if (stateAlarms[entry.key] == true) {
        for (final svgPath in entry.value) {
          if (!svgPath.getBounds().overlaps(visibleRect)) continue;
          canvas.drawPath(svgPath, _pulseFill);
          canvas.drawPath(svgPath, _pulseStroke);
        }
      }
    }

    // Animated alarm color for districts
    final districtAlarmColor = Color.lerp(
      mapColors.isDark ? _distBaseDark : Color.fromRGBO(239, 68, 68, 0.6),
      mapColors.isDark ? _distHighDark : Color.fromRGBO(248, 113, 113, 0.8),
      pulseValue,
    )!;

    _distPulseFill.color = districtAlarmColor.withValues(alpha: 0.7 * opacity);
    _distPulseStroke
      ..color = districtAlarmColor.withValues(alpha: 0.7 * opacity)
      ..strokeWidth = 0.3 * strokeScale;

    // Only draw alarmed districts — with viewport culling
    for (final entry in districtPathsCache.entries) {
      if (districtAlarms[entry.key] == true) {
        for (final svgPath in entry.value) {
          if (!svgPath.getBounds().overlaps(visibleRect)) continue;
          canvas.drawPath(svgPath, _distPulseFill);
          canvas.drawPath(svgPath, _distPulseStroke);
        }
      }
    }

    canvas.restore();
  }

  @override
  bool shouldRepaint(PulseAlarmPainter oldDelegate) {
    // Only repaint on significant pulse changes (reduces from ~30/sec to ~5/sec)
    if ((pulseValue - oldDelegate.pulseValue).abs() > 0.15) return true;
    if (opacity != oldDelegate.opacity) return true;
    // Camera changes — reduced sensitivity
    if ((camera.zoom - oldDelegate.camera.zoom).abs() > 0.05) return true;
    if ((camera.center.latitude - oldDelegate.camera.center.latitude).abs() >
        0.001) {
      return true;
    }
    if ((camera.center.longitude - oldDelegate.camera.center.longitude).abs() >
        0.001) {
      return true;
    }
    // Alarm data changes
    if (!mapEquals(stateAlarms, oldDelegate.stateAlarms)) return true;
    if (!mapEquals(districtAlarms, oldDelegate.districtAlarms)) return true;
    return false;
  }
}

/// Labels and markers layer - always visible regardless of SVG opacity
class LabelsMarkersLayer extends StatelessWidget {
  final List<ThreatMarker> threatMarkers;
  final MapColors mapColors;
  final void Function(ThreatMarker) onMarkerTap;

  const LabelsMarkersLayer({
    super.key,
    required this.threatMarkers,
    required this.mapColors,
    required this.onMarkerTap,
  });

  @override
  Widget build(BuildContext context) {
    final camera = MapCamera.of(context);

    return CustomPaint(
      size: Size.infinite,
      painter: LabelsMarkersPainter(
        camera: camera,
        threatMarkers: threatMarkers,
        mapColors: mapColors,
      ),
    );
  }
}

class LabelsMarkersPainter extends CustomPainter {
  final MapCamera camera;
  final List<ThreatMarker> threatMarkers;
  final MapColors mapColors;

  // Region labels with SVG coordinates
  static const regionLabels = <String, Map<String, dynamic>>{
    'UA-68': {'name': 'Хмельницька', 'x': 68.5, 'y': 63.0},
    'UA-07': {'name': 'Волинська', 'x': 40.0, 'y': 28.2},
    'UA-56': {'name': 'Рівненська', 'x': 65.0, 'y': 30.0},
    'UA-18': {'name': 'Житомирська', 'x': 88.0, 'y': 42.3},
    'UA-32': {'name': 'Київська', 'x': 122.0, 'y': 56.0},
    'UA-30': {'name': 'м. Київ', 'x': 120.0, 'y': 41.5},
    'UA-74': {'name': 'Чернігівська', 'x': 139.0, 'y': 25.5},
    'UA-59': {'name': 'Сумська', 'x': 171.0, 'y': 33.0},
    'UA-63': {'name': 'Харківська', 'x': 203.5, 'y': 62.8},
    'UA-09': {'name': 'Луганська', 'x': 239.0, 'y': 79.0},
    'UA-14': {'name': 'Донецька', 'x': 221.0, 'y': 97.0},
    'UA-23': {'name': 'Запорізька', 'x': 195.0, 'y': 115.0},
    'UA-12': {'name': 'Дніпропетровська', 'x': 178.0, 'y': 89.0},
    'UA-48': {'name': 'Миколаївська', 'x': 139.0, 'y': 113.0},
    'UA-65': {'name': 'Херсонська', 'x': 163.0, 'y': 126.0},
    'UA-51': {'name': 'Одеська', 'x': 110.0, 'y': 138.0},
    'UA-35': {'name': 'Кіровоградська', 'x': 140.0, 'y': 88.4},
    'UA-53': {'name': 'Полтавська', 'x': 162.7, 'y': 58.0},
    'UA-71': {'name': 'Черкаська', 'x': 132.0, 'y': 73.0},
    'UA-05': {'name': 'Вінницька', 'x': 95.0, 'y': 80.0},
    'UA-61': {'name': 'Тернопільська', 'x': 47.0, 'y': 67.0},
    'UA-77': {'name': 'Чернівецька', 'x': 53.0, 'y': 94.0},
    'UA-26': {'name': 'Івано-Франківська', 'x': 32.0, 'y': 83.0},
    'UA-21': {'name': 'Закарпатська', 'x': 15.0, 'y': 91.0},
    'UA-46': {'name': 'Львівська', 'x': 29.0, 'y': 61.0},
    'UA-43': {'name': 'А. Р. Крим', 'x': 172.0, 'y': 152.7},
  };

  // Cached paint for marker icons (avoid allocating on every draw)
  static final Paint _iconPaint = Paint()..filterQuality = FilterQuality.low;

  static Paint _iconPaintWithOpacity(double opacity) {
    if (opacity >= 0.999) return _iconPaint;
    return Paint()
      ..filterQuality = FilterQuality.low
      ..colorFilter = ColorFilter.matrix([
        1,
        0,
        0,
        0,
        0,
        0,
        1,
        0,
        0,
        0,
        0,
        0,
        1,
        0,
        0,
        0,
        0,
        0,
        opacity,
        0,
      ]);
  }

  // Cached TextPainters — avoid 26 TextPainter.layout() calls per frame
  static final Map<String, TextPainter> _labelPainterCache = {};
  static double _cachedLabelSize = 0;
  static bool _cachedIsDark = false;

  LabelsMarkersPainter({
    required this.camera,
    required this.threatMarkers,
    required this.mapColors,
  });

  /// Convert SVG coordinates to screen offset using camera
  Offset svgToScreen(double svgX, double svgY) {
    final latLng = SvgMapLayer.svgToLatLng(svgX, svgY);
    return camera.latLngToScreenOffset(latLng);
  }

  /// Rebuild TextPainter cache only when labelSize or theme changes
  void _ensureLabelCache(double labelSize) {
    if (_labelPainterCache.isNotEmpty &&
        _cachedLabelSize == labelSize &&
        _cachedIsDark == mapColors.isDark) {
      return;
    }
    _cachedLabelSize = labelSize;
    _cachedIsDark = mapColors.isDark;
    _labelPainterCache.clear();

    final labelStyle = TextStyle(
      color: mapColors.labelColor,
      fontSize: labelSize,
      fontWeight: FontWeight.w600,
      shadows: [
        Shadow(
          color: mapColors.labelShadow,
          blurRadius: 2,
          offset: const Offset(0.5, 0.5),
        ),
        Shadow(
          color: mapColors.labelShadow,
          blurRadius: 1,
          offset: const Offset(-0.3, -0.3),
        ),
      ],
    );

    for (final entry in regionLabels.entries) {
      final data = entry.value;
      final name = data['name'] as String;
      final tp = TextPainter(
        text: TextSpan(text: name, style: labelStyle),
        textDirection: TextDirection.ltr,
        textAlign: TextAlign.center,
      )..layout();
      _labelPainterCache[entry.key] = tp;
    }
  }

  @override
  void paint(Canvas canvas, Size size) {
    final strokeScale = (camera.zoom / 6.0).clamp(0.5, 3.0);

    // === THREAT MARKERS (draw first — below labels so oblast names stay readable) ===
    final markerSize = (24.0 * strokeScale).clamp(20.0, 48.0);
    final iconManager = ThreatIconManager();

    for (final marker in threatMarkers) {
      final screenPos = camera.latLngToScreenOffset(
        LatLng(marker.lat, marker.lng),
      );

      // Skip if outside visible area (with margin for rotated icons)
      if (screenPos.dx < -markerSize ||
          screenPos.dx > size.width + markerSize ||
          screenPos.dy < -markerSize ||
          screenPos.dy > size.height + markerSize) {
        continue;
      }

      final color = ThreatType.getColor(marker.threatType);
      final visOp = marker.mapVisualOpacity;

      // Draw icon from cache with rotation (server marker_icon overrides threat type)
      final icon =
          iconManager.getIconForThreatMarker(
            threatType: marker.threatType,
            markerIcon: marker.markerIcon,
          ) ??
          iconManager.icons['default'];

      double? bearingDeg = resolveThreatBearingDeg(marker);
      if (bearingDeg == null &&
          marker.hasTrajectory &&
          marker.projectedPath != null &&
          marker.projectedPath!.length >= 2) {
        final path = marker.projectedPath!;
        final lastIdx = path.length - 1;
        bearingDeg = initialBearingDeg(
          path[lastIdx - 1].lat,
          path[lastIdx - 1].lng,
          path[lastIdx].lat,
          path[lastIdx].lng,
        );
      }

      final rotationAngle = bearingDeg != null
          ? canvasRotationRadMatchingWeb(bearingDeg)
          : 0.0;

      if (icon != null && iconManager.isLoaded) {
        canvas.save();
        canvas.translate(screenPos.dx, screenPos.dy);

        if (rotationAngle != 0.0) {
          canvas.rotate(rotationAngle);
        }

        final srcRect = Rect.fromLTWH(
          0,
          0,
          icon.width.toDouble(),
          icon.height.toDouble(),
        );
        final dstRect = Rect.fromCenter(
          center: Offset.zero,
          width: markerSize,
          height: markerSize,
        );
        canvas.drawImageRect(
          icon,
          srcRect,
          dstRect,
          _iconPaintWithOpacity(visOp),
        );

        canvas.restore();
      } else {
        // Fallback circle when icon not loaded
        final markerPaint = Paint()
          ..color = color.withValues(alpha: 0.9 * visOp)
          ..style = PaintingStyle.fill;
        canvas.drawCircle(screenPos, markerSize / 2, markerPaint);

        final borderPaint = Paint()
          ..color = Colors.white.withValues(alpha: 0.8 * visOp)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2.0;
        canvas.drawCircle(screenPos, markerSize / 2, borderPaint);
      }
    }

    // === REGION LABELS (drawn last — on top so names are never covered by icons) ===
    if (camera.zoom > 4.5) {
      final labelSize = (11.0 * strokeScale).clamp(9.0, 16.0);
      _ensureLabelCache(labelSize);

      for (final entry in regionLabels.entries) {
        final data = entry.value;
        final svgX = data['x'] as double;
        final svgY = data['y'] as double;
        final screenPos = svgToScreen(svgX, svgY);

        // Skip if outside visible area
        if (screenPos.dx < -100 ||
            screenPos.dx > size.width + 100 ||
            screenPos.dy < -50 ||
            screenPos.dy > size.height + 50) {
          continue;
        }

        final tp = _labelPainterCache[entry.key];
        if (tp != null) {
          final offsetX = screenPos.dx - tp.width / 2;
          final offsetY = screenPos.dy - tp.height / 2;
          tp.paint(canvas, Offset(offsetX, offsetY));
        }
      }
    }
  }

  @override
  bool shouldRepaint(LabelsMarkersPainter oldDelegate) {
    if (threatMarkers.length != oldDelegate.threatMarkers.length) return true;
    if ((camera.zoom - oldDelegate.camera.zoom).abs() > 0.01) return true;
    if ((camera.center.latitude - oldDelegate.camera.center.latitude).abs() >
        0.0001) {
      return true;
    }
    if ((camera.center.longitude - oldDelegate.camera.center.longitude).abs() >
        0.0001) {
      return true;
    }
    if (mapColors.isDark != oldDelegate.mapColors.isDark) return true;
    return false;
  }
}
