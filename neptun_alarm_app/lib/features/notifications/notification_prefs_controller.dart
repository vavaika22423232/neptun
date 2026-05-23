import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import '../../config/api_config.dart';
import '../../config/prefs_keys.dart';

/// Локальні налаштування push + синхронізація з бекендом (graceful 404).
class NotificationPrefsController {
  Future<Map<String, dynamic>> buildPayload() async {
    final prefs = await SharedPreferences.getInstance();
    return {
      'notifications_enabled': prefs.getBool('notifications_enabled') ?? true,
      'quiet_hours_enabled': prefs.getBool('quiet_hours_enabled') ?? false,
      'quiet_hours_start': prefs.getString('quiet_hours_start') ?? '22:00',
      'quiet_hours_end': prefs.getString('quiet_hours_end') ?? '07:00',
      'quiet_hours_allow_critical':
          prefs.getBool('quiet_hours_allow_critical') ?? true,
      'notify_threat_types':
          prefs.getStringList('notify_threat_types') ?? <String>[],
      'regions': prefs.getStringList(PrefsKeys.selectedRegions) ?? <String>[],
      'oblast_ids': prefs.getStringList('selected_oblast_ids') ?? <String>[],
      'raion_ids': prefs.getStringList('selected_raion_ids') ?? <String>[],
    };
  }

  Future<void> syncToBackend({
    required String deviceId,
    String? fcmToken,
  }) async {
    final body = await buildPayload();
    body['device_id'] = deviceId;
    if (fcmToken != null && fcmToken.isNotEmpty) {
      body['token'] = fcmToken;
    }

    try {
      final response = await http
          .patch(
            Uri.parse(ApiConfig.devicePreferences),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode(body),
          )
          .timeout(ApiConfig.httpTimeout);

      if (response.statusCode == 404 || response.statusCode == 405) {
        if (kDebugMode) {
          debugPrint(
            'NotificationPrefsController: preferences API not available (${response.statusCode})',
          );
        }
        return;
      }
      if (response.statusCode >= 200 && response.statusCode < 300) {
        if (kDebugMode) {
          debugPrint('NotificationPrefsController: synced preferences');
        }
        return;
      }
      debugPrint(
        'NotificationPrefsController: sync failed HTTP ${response.statusCode}',
      );
    } catch (e) {
      debugPrint('NotificationPrefsController: sync error: $e');
    }
  }
}
