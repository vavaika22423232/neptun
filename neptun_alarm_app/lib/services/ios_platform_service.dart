import 'dart:io';
import 'package:flutter/services.dart';
import 'package:flutter/foundation.dart';

/// iOS-specific platform service for native features
/// Handles haptic feedback, badge counts, and other iOS-specific functionality
class IOSPlatformService {
  static final IOSPlatformService _instance = IOSPlatformService._internal();
  factory IOSPlatformService() => _instance;
  IOSPlatformService._internal();

  static const _channel = MethodChannel('ua.neptun.app/ios');
  bool _initialized = false;

  /// Initialize the iOS platform service
  void initialize() {
    if (!Platform.isIOS || _initialized) return;

    _channel.setMethodCallHandler(_handleMethodCall);
    _initialized = true;
    debugPrint('✅ IOSPlatformService initialized');
  }

  /// Handle method calls from native iOS
  Future<dynamic> _handleMethodCall(MethodCall call) async {
    switch (call.method) {
      case 'onBackgroundRefresh':
        debugPrint('📱 Background refresh triggered');
        // Handle background refresh - can trigger alarm check here
        return null;
      case 'onFCMToken':
        final token = call.arguments as String?;
        if (kDebugMode) {
          debugPrint(
            '📱 FCM Token received: ${token != null ? '${token.substring(0, token.length < 20 ? token.length : 20)}...' : 'null'}',
          );
        }
        return null;
      case 'onNotificationTapped':
        if (kDebugMode) debugPrint('📱 Notification tapped: ${call.arguments}');
        return null;
      case 'onAPNSTokenReceived':
        final token = call.arguments as String?;
        if (kDebugMode) {
          debugPrint(
            '🍎✅ APNS Token received: ${token != null ? '${token.substring(0, token.length < 20 ? token.length : 20)}...' : 'null'}',
          );
        }
        return null;
      case 'onAPNSError':
        final error = call.arguments as String? ?? '';
        // aps-environment missing is expected on Simulator; be less alarming
        final isExpectedOnSimulator = error.toLowerCase().contains('aps-environment') ||
            error.contains('не найдены') ||
            error.contains('not found');
        if (kDebugMode) {
          if (isExpectedOnSimulator) {
            debugPrint(
              '🍎 APNS not available: $error (expected on Simulator; use real device for push)',
            );
          } else {
            debugPrint('🍎❌ APNS Registration FAILED: $error');
          }
        }
        return null;
      default:
        return null;
    }
  }

  /// Trigger haptic feedback (iOS only)
  /// Types: light, medium, heavy, selection, success, warning, error
  Future<void> hapticFeedback(HapticType type) async {
    if (!Platform.isIOS) {
      // Fallback to Flutter haptics on Android
      switch (type) {
        case HapticType.light:
          await HapticFeedback.lightImpact();
          break;
        case HapticType.medium:
          await HapticFeedback.mediumImpact();
          break;
        case HapticType.heavy:
          await HapticFeedback.heavyImpact();
          break;
        case HapticType.selection:
          await HapticFeedback.selectionClick();
          break;
        default:
          await HapticFeedback.mediumImpact();
      }
      return;
    }

    try {
      await _channel.invokeMethod('hapticFeedback', type.name);
    } catch (e) {
      debugPrint('Haptic feedback error: $e');
    }
  }

  /// Set app badge count (iOS only)
  Future<void> setBadgeCount(int count) async {
    if (!Platform.isIOS) return;

    try {
      await _channel.invokeMethod('setBadgeCount', count);
    } catch (e) {
      debugPrint('Set badge count error: $e');
    }
  }

  /// Clear app badge
  Future<void> clearBadge() async {
    await setBadgeCount(0);
  }

  /// Get device info
  Future<Map<String, dynamic>?> getDeviceInfo() async {
    if (!Platform.isIOS) return null;

    try {
      final result = await _channel.invokeMethod('getDeviceInfo');
      return Map<String, dynamic>.from(result);
    } catch (e) {
      debugPrint('Get device info error: $e');
      return null;
    }
  }
}

/// Haptic feedback types
enum HapticType { light, medium, heavy, selection, success, warning, error }

/// Extension for easy haptic access
extension HapticFeedbackExtension on HapticType {
  Future<void> trigger() => IOSPlatformService().hapticFeedback(this);
}
