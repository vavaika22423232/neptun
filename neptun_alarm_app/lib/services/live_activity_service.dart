import 'dart:io';
import 'package:flutter/services.dart';
import 'package:flutter/foundation.dart';

/// iOS Live Activity service for Dynamic Island and Lock Screen.
/// Requires iOS 16.1+. No-op on Android and older iOS.
class LiveActivityService {
  static final LiveActivityService _instance = LiveActivityService._internal();
  factory LiveActivityService() => _instance;
  LiveActivityService._internal();

  static const _channel = MethodChannel('ua.neptun.app/ios');

  /// Start Live Activity when alarm begins.
  /// [region] - region name (e.g. "Київська область")
  /// [threatType] - air, ballistic, drones
  /// [threatCount] - number of threats (for display)
  /// [isAlarm] - true for active alarm
  Future<void> start({
    required String region,
    String threatType = 'air',
    int threatCount = 1,
    bool isAlarm = true,
  }) async {
    if (!Platform.isIOS) return;

    try {
      await _channel.invokeMethod('startLiveActivity', {
        'region': region,
        'threatType': threatType,
        'threatCount': threatCount,
        'isAlarm': isAlarm,
      });
      if (kDebugMode) {
        debugPrint('📱 Live Activity started: $region ($threatType)');
      }
    } on PlatformException catch (e) {
      if (kDebugMode) {
        debugPrint('📱 Live Activity start error: ${e.message}');
      }
    }
  }

  /// Update Live Activity with new threat count or state.
  Future<void> update({
    required String region,
    String threatType = 'air',
    int threatCount = 1,
    bool isAlarm = true,
    DateTime? startTime,
  }) async {
    if (!Platform.isIOS) return;

    try {
      await _channel.invokeMethod('updateLiveActivity', {
        'region': region,
        'threatType': threatType,
        'threatCount': threatCount,
        'isAlarm': isAlarm,
        if (startTime != null) 'startTimeMs': startTime.millisecondsSinceEpoch,
      });
    } on PlatformException catch (e) {
      if (kDebugMode) {
        debugPrint('📱 Live Activity update error: ${e.message}');
      }
    }
  }

  /// End Live Activity when alarm clears.
  Future<void> end() async {
    if (!Platform.isIOS) return;

    try {
      await _channel.invokeMethod('endLiveActivity');
      if (kDebugMode) {
        debugPrint('📱 Live Activity ended');
      }
    } on PlatformException catch (e) {
      if (kDebugMode) {
        debugPrint('📱 Live Activity end error: ${e.message}');
      }
    }
  }
}
