import 'dart:io';
import 'package:flutter/services.dart';
import 'package:flutter/foundation.dart';

/// Android-specific platform service
/// Provides native Android features via Method Channel
class AndroidPlatformService {
  static final AndroidPlatformService _instance = AndroidPlatformService._internal();
  factory AndroidPlatformService() => _instance;
  AndroidPlatformService._internal();
  
  static const _channel = MethodChannel('ua.neptun.app/android');
  
  bool _initialized = false;
  Map<String, dynamic>? _deviceInfo;
  
  /// Initialize the service
  Future<void> initialize() async {
    if (_initialized || !Platform.isAndroid) return;
    
    try {
      _deviceInfo = await getDeviceInfo();
      _initialized = true;
      debugPrint('AndroidPlatformService initialized');
    } catch (e) {
      debugPrint('AndroidPlatformService init error: $e');
    }
  }
  
  /// Perform haptic feedback
  /// Types: light, medium, heavy, selection, success, warning, error
  Future<void> haptic(String type) async {
    if (!Platform.isAndroid) return;
    try {
      await _channel.invokeMethod('haptic', {'type': type});
    } catch (e) {
      debugPrint('Haptic error: $e');
    }
  }
  
  /// Light haptic feedback (for taps)
  Future<void> hapticLight() => haptic('light');
  
  /// Medium haptic feedback (for toggles)
  Future<void> hapticMedium() => haptic('medium');
  
  /// Heavy haptic feedback (for important actions)
  Future<void> hapticHeavy() => haptic('heavy');
  
  /// Selection haptic feedback
  Future<void> hapticSelection() => haptic('selection');
  
  /// Success haptic feedback
  Future<void> hapticSuccess() => haptic('success');
  
  /// Warning haptic feedback
  Future<void> hapticWarning() => haptic('warning');
  
  /// Error haptic feedback
  Future<void> hapticError() => haptic('error');
  
  /// Vibrate for a duration
  Future<void> vibrate({int durationMs = 100}) async {
    if (!Platform.isAndroid) return;
    try {
      await _channel.invokeMethod('vibrate', {'duration': durationMs});
    } catch (e) {
      debugPrint('Vibrate error: $e');
    }
  }
  
  /// Vibrate with a pattern
  /// Pattern: [delay, vibrate, delay, vibrate, ...]
  Future<void> vibratePattern(List<int> pattern) async {
    if (!Platform.isAndroid) return;
    try {
      await _channel.invokeMethod('vibrate', {'pattern': pattern});
    } catch (e) {
      debugPrint('Vibrate pattern error: $e');
    }
  }
  
  /// Alarm vibration pattern
  Future<void> vibrateAlarm() => vibratePattern([0, 500, 200, 500, 200, 500]);
  
  /// Check if battery optimization is disabled for the app
  Future<bool> isBatteryOptimizationDisabled() async {
    if (!Platform.isAndroid) return true;
    try {
      final result = await _channel.invokeMethod<bool>('isBatteryOptimizationDisabled');
      return result ?? false;
    } catch (e) {
      debugPrint('Battery optimization check error: $e');
      return false;
    }
  }
  
  /// Request user to disable battery optimization
  /// This is important for reliable alarm notifications
  Future<void> requestDisableBatteryOptimization() async {
    if (!Platform.isAndroid) return;
    try {
      await _channel.invokeMethod('requestDisableBatteryOptimization');
    } catch (e) {
      debugPrint('Battery optimization request error: $e');
    }
  }
  
  /// Clear all notification badges
  Future<void> clearBadge() async {
    if (!Platform.isAndroid) return;
    try {
      await _channel.invokeMethod('clearBadge');
    } catch (e) {
      debugPrint('Clear badge error: $e');
    }
  }
  
  /// Set notification badge count
  Future<void> setBadge(int count) async {
    if (!Platform.isAndroid) return;
    try {
      await _channel.invokeMethod('setBadge', {'count': count});
    } catch (e) {
      debugPrint('Set badge error: $e');
    }
  }
  
  /// Get device information
  Future<Map<String, dynamic>> getDeviceInfo() async {
    if (_deviceInfo != null) return _deviceInfo!;
    if (!Platform.isAndroid) return {};
    
    try {
      final result = await _channel.invokeMethod<Map>('getDeviceInfo');
      _deviceInfo = Map<String, dynamic>.from(result ?? {});
      return _deviceInfo!;
    } catch (e) {
      debugPrint('Get device info error: $e');
      return {};
    }
  }
  
  /// Keep screen on (useful during alarms)
  Future<void> keepScreenOn(bool enable) async {
    if (!Platform.isAndroid) return;
    try {
      await _channel.invokeMethod('keepScreenOn', {'enable': enable});
    } catch (e) {
      debugPrint('Keep screen on error: $e');
    }
  }
  
  /// Check if app can bypass Do Not Disturb
  Future<bool> canBypassDnd() async {
    if (!Platform.isAndroid) return false;
    try {
      final result = await _channel.invokeMethod<bool>('canBypassDnd');
      return result ?? false;
    } catch (e) {
      debugPrint('Can bypass DND check error: $e');
      return false;
    }
  }
  
  /// Open app settings
  Future<void> openAppSettings() async {
    if (!Platform.isAndroid) return;
    try {
      await _channel.invokeMethod('openAppSettings');
    } catch (e) {
      debugPrint('Open app settings error: $e');
    }
  }
  
  /// Open notification settings
  Future<void> openNotificationSettings() async {
    if (!Platform.isAndroid) return;
    try {
      await _channel.invokeMethod('openNotificationSettings');
    } catch (e) {
      debugPrint('Open notification settings error: $e');
    }
  }
  
  // ============== Getters ==============
  
  /// Get device manufacturer
  String get manufacturer => _deviceInfo?['manufacturer'] ?? 'Unknown';
  
  /// Get device model
  String get model => _deviceInfo?['model'] ?? 'Unknown';
  
  /// Get device brand
  String get brand => _deviceInfo?['brand'] ?? 'Unknown';
  
  /// Get Android SDK version
  int get sdkVersion => _deviceInfo?['sdkInt'] ?? 0;
  
  /// Get Android release version (e.g., "14")
  String get androidVersion => _deviceInfo?['release'] ?? 'Unknown';
  
  /// Check if running on emulator
  bool get isEmulator => _deviceInfo?['isEmulator'] ?? false;
  
  /// Get full device name
  String get deviceName => '$brand $model';
  
  /// Check if device is Samsung (for specific optimizations)
  bool get isSamsung => brand.toLowerCase() == 'samsung';
  
  /// Check if device is Xiaomi (aggressive battery optimization)
  bool get isXiaomi => brand.toLowerCase().contains('xiaomi') || 
                        brand.toLowerCase().contains('redmi') ||
                        brand.toLowerCase().contains('poco');
  
  /// Check if device is Huawei (aggressive battery optimization)
  bool get isHuawei => brand.toLowerCase().contains('huawei') ||
                        brand.toLowerCase().contains('honor');
  
  /// Check if device needs aggressive battery optimization disabled
  bool get needsBatteryOptimizationWarning => isXiaomi || isHuawei;
}
