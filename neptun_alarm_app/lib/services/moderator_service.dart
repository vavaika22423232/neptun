import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../config/api_config.dart';
import 'package:neptun_alarm_app/core/utils/app_debug_log.dart';
import 'auth_service.dart';

/// Singleton service managing moderator authentication state.
/// Skips Keychain entirely in debug iOS builds (Simulator) to avoid
/// PlatformException -34018.
class ModeratorService {
  ModeratorService._();
  static final ModeratorService instance = ModeratorService._();

  static const _kModSecret = '_mod_secret';
  static const _kFallbackKey = '_mod_secret_fb';

  /// Upper bound for moderator secret length (payload / abuse mitigation).
  static const int maxModeratorSecretLength = 256;

  /// Client-side validation before network. Returns Ukrainian error or null if OK.
  static String? validateModeratorSecretInput(String raw) {
    final s = raw.trim();
    if (s.isEmpty || s.length < 6) return 'Введіть пароль';
    if (s.length > maxModeratorSecretLength) {
      return 'Пароль занадто довгий';
    }
    return null;
  }

  static const _secureStorage = FlutterSecureStorage(
    iOptions: IOSOptions(
      accessibility: KeychainAccessibility.first_unlock,
      accountName: 'com.neptunalarm.neptunAlarmApp',
    ),
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
  );

  static bool get _useKeychain => !(kDebugMode && Platform.isIOS);

  bool _isModerator = false;
  String? _deviceId;

  bool get isModerator => _isModerator;

  /// Для [ListenableBuilder] у шеллі — без [setState] на кожен евент стріму.
  final ValueNotifier<bool> isModeratorNotifier = ValueNotifier(false);

  final _controller = StreamController<bool>.broadcast();
  Stream<bool> get stream => _controller.stream;

  // ── Init ─────────────────────────────────────────────────────────────
  Future<void> init([String? deviceId]) async {
    final prefs = await SharedPreferences.getInstance();

    _deviceId = deviceId ?? await AuthService.getDeviceId();
    _isModerator = prefs.getBool('chat_moderator') ?? false;
    isModeratorNotifier.value = _isModerator;
    _controller.add(_isModerator);
    // Pre-warm secure storage to avoid first-access freeze during login
    await _readSecret();
  }

  // ── Secure read / write / delete ────────────────────────────────────
  Future<String?> _readSecret() async {
    if (_useKeychain) {
      return _secureStorage.read(key: _kModSecret);
    }
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_kFallbackKey);
  }

  Future<void> _writeSecret(String value) async {
    if (_useKeychain) {
      await _secureStorage.write(key: _kModSecret, value: value);
    } else {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_kFallbackKey, value);
    }
  }

  Future<void> _deleteSecret() async {
    if (_useKeychain) {
      await _secureStorage.delete(key: _kModSecret);
    }
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_kFallbackKey);
  }

  // ── Login ────────────────────────────────────────────────────────────
  Future<String?> login(String secret) async {
    if (_deviceId == null) return 'Device ID not initialized';
    final validation = validateModeratorSecretInput(secret);
    if (validation != null) return validation;
    final trimmed = secret.trim();

    try {
      final response = await http
          .post(
            Uri.parse(ApiConfig.chatAddModerator),
            headers: {'Content-Type': 'application/json'},
            body: json.encode({'secret': trimmed, 'deviceId': _deviceId}),
          )
          .timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final prefs = await SharedPreferences.getInstance();
        await prefs.setBool('chat_moderator', true);
        await prefs.setInt(
          'moderator_login_time',
          DateTime.now().millisecondsSinceEpoch,
        );
        await _writeSecret(trimmed);

        _isModerator = true;
        isModeratorNotifier.value = true;
        _controller.add(true);
        return null;
      } else {
        final body = utf8.decode(response.bodyBytes);
        if (body.trimLeft().startsWith('<')) {
          return 'Помилка сервера (${response.statusCode})';
        }
        try {
          final data = json.decode(body) as Map<String, dynamic>?;
          return data?['error']?.toString() ?? 'Невірний пароль';
        } catch (_) {
          return 'Помилка сервера (${response.statusCode})';
        }
      }
    } catch (e) {
      appDebugLog('❌ ModeratorService.login error: $e');
      return 'Помилка з\'єднання';
    }
  }

  // ── Logout ───────────────────────────────────────────────────────────
  Future<void> logout() async {
    try {
      if (_deviceId != null && _deviceId!.isNotEmpty) {
        final secret = await _readSecret() ?? '';
        await http
            .post(
              Uri.parse(ApiConfig.chatRemoveModerator),
              headers: {'Content-Type': 'application/json'},
              body: json.encode({'secret': secret, 'deviceId': _deviceId}),
            )
            .timeout(const Duration(seconds: 10));
      }
    } catch (e) {
      appDebugLog('❌ ModeratorService.logout error: $e');
    }

    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('chat_moderator', false);
    await prefs.remove('moderator_login_time');
    await _deleteSecret();

    _isModerator = false;
    isModeratorNotifier.value = false;
    _controller.add(false);
  }

  /// Read the stored secret for authenticated API calls (e.g. admin panel).
  Future<String?> getSecret() async => _readSecret();

  void dispose() {
    _controller.close();
  }
}
