import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'dart:ui' as ui;
import 'package:jovial_svg/jovial_svg.dart';

class ThreatIconManager {
  static final ThreatIconManager _instance = ThreatIconManager._internal();
  factory ThreatIconManager() => _instance;
  ThreatIconManager._internal();

  final Map<String, ui.Image?> _icons = {};
  bool _isLoading = false;
  bool _isLoaded = false;

  static const Map<String, String> iconAssets = {
    'shahed': 'assets/icons/shahed3.png',
    'air_balloon': 'assets/icons/icon_air_balloon.svg',
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
      debugPrint('Failed to load icon $key: $e');
      _icons[key] = null;
    }
  }

  ui.Image? getIcon(String threatType) {
    return _icons[threatType] ?? _icons['default'];
  }

  /// Іконка з урахуванням `marker_icon` з API (ім'я файлу → ключ кешу).
  ui.Image? getIconForThreatMarker({
    required String threatType,
    String? markerIcon,
  }) {
    if (markerIcon == null || markerIcon.isEmpty) {
      return getIcon(threatType);
    }
    var key = markerIcon.toLowerCase().trim();
    key = key.replaceAll(RegExp(r'\.(png|webp|svg|jpg|jpeg)$'), '');
    key = key.replaceAll(RegExp(r'^/+'), '');

    if (_icons.containsKey(key) && _icons[key] != null) {
      return _icons[key];
    }

    const aliases = <String, String>{
      'shahed3': 'shahed',
      'fpvdrone': 'fpv',
      'icon_drone': 'fpv',
      'drone': 'fpv',
      'icon_balistic': 'raketa',
      'icon_missile': 'kab',
      'icon_obstril': 'obstril',
      'icon_vibuh': 'vibuh',
      'rozvedka2': 'rozved',
      'pusk': 'pusk',
      'kab': 'kab',
      'raketa': 'raketa',
      'avia': 'avia',
      'artillery': 'artillery',
      'fpv': 'fpv',
      'shahed': 'shahed',
      'obstril': 'obstril',
      'vibuh': 'vibuh',
      'trivoga': 'trivoga',
      'vidboi': 'vidboi',
      'rszv': 'rszv',
      'rozved': 'rozved',
      'icon_air_balloon': 'air_balloon',
      'balloon': 'air_balloon',
      'air_balloon': 'air_balloon',
      'default': 'default',
    };

    final mapped = aliases[key];
    if (mapped != null && _icons[mapped] != null) {
      return _icons[mapped];
    }

    return getIcon(threatType);
  }

  Map<String, ui.Image?> get icons => _icons;
}
