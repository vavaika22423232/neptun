import 'package:flutter/foundation.dart';

/// Global notifier that signals when the main map WebView has finished loading.
/// MapTab sets [value] = true on `onPageFinished`.
/// The splash screen listens to this to dismiss itself.
class MapReadyNotifier extends ValueNotifier<bool> {
  MapReadyNotifier._() : super(false);

  static final MapReadyNotifier instance = MapReadyNotifier._();

  /// Call once the map WebView's onPageFinished fires (or on error/fallback).
  void markReady() {
    if (!value) {
      value = true;
      debugPrint('🗺️ MapReadyNotifier: map is ready');
    }
  }

  /// Reset for testing or hot-restart scenarios.
  void reset() => value = false;
}
