import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'dart:ui' as ui;
import 'package:jovial_svg/jovial_svg.dart';
import 'package:neptun_alarm_app/core/utils/app_debug_log.dart';

class ThreatIconManager {
  static final ThreatIconManager _instance = ThreatIconManager._internal();
  factory ThreatIconManager() => _instance;
  ThreatIconManager._internal();

  final Map<String, ui.Image?> _icons = {};
  bool _isLoading = false;
  bool _isLoaded = false;

  static const Map<String, String> iconAssets = {
    /// API `marker_icon` fpvdrone.png (e.g. @kherson_non_drone channel)
    'marker_fpvdrone': 'assets/icons/fpvdrone.png',
    'shahed': 'assets/icons/shahed3.png',
    'raketa': 'assets/icons/icon_balistic.svg',
    'avia': 'assets/icons/avia.png',
    'artillery': 'assets/icons/artillery.png',
    'obstril': 'assets/icons/icon_obstril.svg',
    'fpv': 'assets/icons/fpv.png',
    'pusk': 'assets/icons/icon_balistic.svg',
    'kab': 'assets/icons/icon_missile.svg',
    'rszv': 'assets/icons/rszv.png',
    'rozved': 'assets/icons/rozvedka2.png',
    'vibuh': 'assets/icons/icon_vibuh.svg',
    'trivoga': 'assets/icons/trivoga.png',
    'vidboi': 'assets/icons/vidboi.png',
    'default': 'assets/icons/default.png',
  };

  bool get isLoaded => _isLoaded;

  // Render at higher resolution for better quality
  static const int iconSize = 64;

  Future<void> loadIcons() async {
    if (_isLoading || _isLoaded) return;
    _isLoading = true;

    // Load all icons in parallel instead of serially
    await Future.wait(
      iconAssets.entries.map(
        (entry) => _loadSingleIcon(entry.key, entry.value),
      ),
    );

    _isLoaded = true;
    _isLoading = false;
  }

  Future<void> _loadSingleIcon(String key, String path) async {
    try {
      if (path.endsWith('.svg')) {
        // Load SVG and render to ui.Image using jovial_svg
        final svgString = await rootBundle.loadString(path);
        final si = ScalableImage.fromSvgString(svgString);

        // Render at 2x resolution for crisp icons
        final double targetSize = iconSize.toDouble();
        final recorder = ui.PictureRecorder();
        final canvas = Canvas(
          recorder,
          Rect.fromLTWH(0, 0, targetSize, targetSize),
        );

        // Calculate uniform scale to fit in square, maintaining aspect ratio
        final svgWidth = si.viewport.width;
        final svgHeight = si.viewport.height;
        final scale =
            targetSize / (svgWidth > svgHeight ? svgWidth : svgHeight);

        // Center the SVG in the square
        final scaledWidth = svgWidth * scale;
        final scaledHeight = svgHeight * scale;
        final offsetX = (targetSize - scaledWidth) / 2;
        final offsetY = (targetSize - scaledHeight) / 2;

        canvas.translate(offsetX, offsetY);
        canvas.scale(scale, scale);
        si.paint(canvas);

        final picture = recorder.endRecording();
        final image = await picture.toImage(iconSize, iconSize);
        _icons[key] = image;
      } else {
        // Load PNG at higher resolution
        final data = await rootBundle.load(path);
        final codec = await ui.instantiateImageCodec(
          data.buffer.asUint8List(),
          targetWidth: iconSize,
          targetHeight: iconSize,
        );
        final frame = await codec.getNextFrame();
        _icons[key] = frame.image;
      }
    } catch (e) {
      appDebugLog('Failed to load icon $key: $e');
      _icons[key] = null;
    }
  }

  ui.Image? getIcon(String threatType) {
    return _icons[threatType] ?? _icons['default'];
  }

  /// Prefer server [`marker_icon`] when set (filename under /public on web → bundled asset key here).
  ui.Image? getIconForThreatMarker({
    required String threatType,
    String? markerIcon,
  }) {
    final fn = (markerIcon ?? '').toLowerCase();
    if (fn.contains('fpvdrone')) {
      return _icons['marker_fpvdrone'] ?? _icons[threatType] ?? _icons['default'];
    }
    return getIcon(threatType);
  }

  Map<String, ui.Image?> get icons => _icons;
}
