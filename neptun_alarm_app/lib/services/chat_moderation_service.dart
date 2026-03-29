import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter/foundation.dart';
import '../config/api_config.dart';

/// Flutter service for community management and user safety.
/// Manages the local device blocklist and reports messages to backend.
class ChatModerationService extends ChangeNotifier {
  static final ChatModerationService instance = ChatModerationService._();
  ChatModerationService._();

  List<String> _blockedUserIds = [];
  bool _initialized = false;

  /// Get the current subset of locally blocked user IDs / nicknames
  List<String> get blockedUserIds => _blockedUserIds;

  /// Load existing blocked users from disk
  Future<void> init() async {
    if (_initialized) return;
    final prefs = await SharedPreferences.getInstance();
    _blockedUserIds = prefs.getStringList('blocked_users') ?? [];
    _initialized = true;
    notifyListeners();
  }

  /// Evaluates whether a user's nickname is blacklisted on this device
  bool isUserBlocked(String userId) {
    if (!_initialized) return false;
    return _blockedUserIds.contains(userId);
  }

  /// Add a targeted user by their nick / id to the system preferences blocklist
  Future<void> blockUser(String userId) async {
    if (!_blockedUserIds.contains(userId)) {
      _blockedUserIds.add(userId);
      final prefs = await SharedPreferences.getInstance();
      await prefs.setStringList('blocked_users', _blockedUserIds);
      notifyListeners();
    }
  }

  /// Remove a user from local blocklist
  Future<void> unblockUser(String userId) async {
    if (_blockedUserIds.contains(userId)) {
      _blockedUserIds.remove(userId);
      final prefs = await SharedPreferences.getInstance();
      await prefs.setStringList('blocked_users', _blockedUserIds);
      notifyListeners();
    }
  }

  /// Send a formal community report to the backend for an offensive message
  Future<bool> reportMessage({
    required String messageId,
    required String reason,
    required String reporterDeviceId,
    required String reporterNickname,
    String? originalText,
  }) async {
    try {
      final response = await http
          .post(
            Uri.parse(ApiConfig.chatReport),
            headers: {'Content-Type': 'application/json'},
            body: json.encode({
              'messageId': messageId,
              'reason': reason,
              'reporterDeviceId': reporterDeviceId,
              'reporterNickname': reporterNickname,
              'originalText': originalText ?? '',
            }),
          )
          .timeout(const Duration(seconds: 10));

      // Successfully filed report logic
      return response.statusCode == 200 || response.statusCode == 201;
    } catch (e) {
      debugPrint('Error reporting message: $e');
      return false;
    }
  }
}
