import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../config/api_config.dart';
import 'auth_service.dart';

/// Singleton service managing moderator authentication state.
/// Skips Keychain entirely in debug iOS builds (Simulator) to avoid
/// PlatformException -34018.
class ModeratorService {
  ModeratorService._();
  static final ModeratorService instance = ModeratorService._();

  static const _kModSecret = '_mod_secret';
  static const _kFallbackKey = '_mod_secret_fb';

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

  final _controller = StreamController<bool>.broadcast();
  Stream<bool> get stream => _controller.stream;

  // ── Init ─────────────────────────────────────────────────────────────
  Future<void> init([String? deviceId]) async {
    final prefs = await SharedPreferences.getInstance();

    _deviceId = deviceId ?? await AuthService.getDeviceId();
    _isModerator = prefs.getBool('chat_moderator') ?? false;
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
    if (secret.isEmpty || secret.length < 6) return 'Введіть пароль';

    try {
      final response = await http
          .post(
            Uri.parse(ApiConfig.chatAddModerator),
            headers: {'Content-Type': 'application/json'},
            body: json.encode({'secret': secret, 'deviceId': _deviceId}),
          )
          .timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final prefs = await SharedPreferences.getInstance();
        await prefs.setBool('chat_moderator', true);
        await prefs.setInt(
          'moderator_login_time',
          DateTime.now().millisecondsSinceEpoch,
        );
        await _writeSecret(secret);

        _isModerator = true;
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
      debugPrint('❌ ModeratorService.login error: $e');
      return 'Помилка з\'єднання';
    }
  }

  // ── Logout ───────────────────────────────────────────────────────────
  Future<void> logout() async {
    try {
      final secret = await _readSecret() ?? '';
      await http
          .post(
            Uri.parse(ApiConfig.chatRemoveModerator),
            headers: {'Content-Type': 'application/json'},
            body: json.encode({'secret': secret, 'deviceId': _deviceId}),
          )
          .timeout(const Duration(seconds: 10));
    } catch (e) {
      debugPrint('❌ ModeratorService.logout error: $e');
    }

    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('chat_moderator', false);
    await prefs.remove('moderator_login_time');
    await _deleteSecret();

    _isModerator = false;
    _controller.add(false);
  }

  /// Read the stored secret for authenticated API calls (e.g. admin panel).
  Future<String?> getSecret() async => _readSecret();

  void dispose() {
    _controller.close();
  }
}
