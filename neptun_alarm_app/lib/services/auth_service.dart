import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:neptun_alarm_app/config/api_config.dart';

/// JWT Authentication Service for Neptun App
///
/// In debug mode on iOS (simulator) Keychain is unavailable, so we skip it
/// entirely and use SharedPreferences. In release / Android we use
/// FlutterSecureStorage normally.
class AuthService {
  static const String _accessTokenKey = 'jwt_access_token';
  static const String _refreshTokenKey = 'jwt_refresh_token';
  static const String _tokenExpiryKey = 'jwt_token_expiry';
  static const String _deviceIdKey = 'chat_device_id';

  static const _secureStorage = FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
    iOptions: IOSOptions(
      accessibility: KeychainAccessibility.first_unlock,
      accountName: 'com.neptunalarm.neptunAlarmApp',
    ),
  );

  static String? _cachedAccessToken;
  static DateTime? _cachedTokenExpiry;

  /// Skip Keychain entirely in debug iOS builds (Simulator has no entitlements).
  static bool get _useKeychain => !(kDebugMode && Platform.isIOS);

  /// No-op now — kept for backward compat so callers don't break.
  static Future<void> initProbe() async {}

  // ── Storage helpers (never touch Keychain on debug iOS) ─────────────
  static Future<String?> _read(String key) async {
    if (_useKeychain) {
      return _secureStorage.read(key: key);
    }
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('_auth_fb_$key');
  }

  static Future<void> _write(String key, String value) async {
    if (_useKeychain) {
      await _secureStorage.write(key: key, value: value);
    } else {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('_auth_fb_$key', value);
    }
  }

  static Map<String, dynamic>? _tryDecodeJson(String body) {
    final trimmed = body.trim();
    if (trimmed.isEmpty || !trimmed.startsWith('{')) return null;
    try {
      final decoded = json.decode(body);
      return decoded is Map<String, dynamic> ? decoded : null;
    } catch (_) {
      return null;
    }
  }

  static Future<void> _delete(String key) async {
    if (_useKeychain) {
      await _secureStorage.delete(key: key);
    }
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('_auth_fb_$key');
  }

  // ── Public API (unchanged signatures) ───────────────────────────────

  static String? _cachedDeviceId;

  static Future<String> getDeviceId() async {
    if (_cachedDeviceId != null) return _cachedDeviceId!;

    // Try secure storage first
    String? deviceId = await _read(_deviceIdKey);

    if (deviceId == null) {
      // Migrate from SharedPreferences if present
      final prefs = await SharedPreferences.getInstance();
      deviceId = prefs.getString('chat_device_id');
      if (deviceId != null) {
        await _write(_deviceIdKey, deviceId);
        await prefs.remove('chat_device_id');
      }
    }

    if (deviceId == null) {
      deviceId =
          'device_${DateTime.now().millisecondsSinceEpoch}_${DateTime.now().microsecondsSinceEpoch % 999999}';
      await _write(_deviceIdKey, deviceId);
    }

    _cachedDeviceId = deviceId;
    return deviceId;
  }

  static Future<bool> hasValidToken() async {
    final token = await getAccessToken();
    if (token == null) return false;

    final expiry = await _getTokenExpiry();
    if (expiry == null) return false;

    return expiry.isAfter(DateTime.now().add(const Duration(minutes: 5)));
  }

  static Future<String?> getAccessToken() async {
    if (_cachedAccessToken != null && _cachedTokenExpiry != null) {
      if (_cachedTokenExpiry!.isAfter(
        DateTime.now().add(const Duration(minutes: 5)),
      )) {
        return _cachedAccessToken;
      }
    }

    String? token = await _read(_accessTokenKey);

    if (token != null) {
      final expiry = await _getTokenExpiry();
      if (expiry != null &&
          expiry.isAfter(DateTime.now().add(const Duration(minutes: 5)))) {
        _cachedAccessToken = token;
        _cachedTokenExpiry = expiry;
        return token;
      }

      final refreshed = await refreshToken();
      if (refreshed) {
        return _cachedAccessToken;
      }
    }

    return null;
  }

  static Future<String?> getRefreshToken() async {
    return await _read(_refreshTokenKey);
  }

  static Future<DateTime?> _getTokenExpiry() async {
    final expiryStr = await _read(_tokenExpiryKey);
    if (expiryStr == null) return null;
    return DateTime.tryParse(expiryStr);
  }

  static Future<bool> login({String? nickname}) async {
    try {
      final deviceId = await getDeviceId();

      final response = await http
          .post(
            Uri.parse(ApiConfig.authToken),
            headers: {'Content-Type': 'application/json'},
            body: json.encode({'deviceId': deviceId, 'nickname': nickname}),
          )
          .timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final data = _tryDecodeJson(response.body);
        if (data == null) return false;
        await _saveTokens(
          accessToken: data['access_token'],
          refreshToken: data['refresh_token'],
          expiresIn: data['expires_in'],
        );
        return true;
      }

      return false;
    } catch (e) {
      debugPrint('AuthService.login error: $e');
      return false;
    }
  }

  static Future<bool> refreshToken() async {
    try {
      final refreshToken = await getRefreshToken();
      if (refreshToken == null) return false;

      final response = await http
          .post(
            Uri.parse(ApiConfig.authRefresh),
            headers: {'Content-Type': 'application/json'},
            body: json.encode({'refresh_token': refreshToken}),
          )
          .timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final data = _tryDecodeJson(response.body);
        if (data == null) return false;
        await _saveTokens(
          accessToken: data['access_token'],
          refreshToken: null,
          expiresIn: data['expires_in'],
        );
        return true;
      }

      await logout();
      return false;
    } catch (e) {
      debugPrint('AuthService.refreshToken error: $e');
      return false;
    }
  }

  static Future<void> _saveTokens({
    required String accessToken,
    String? refreshToken,
    required int expiresIn,
  }) async {
    final expiry = DateTime.now().add(Duration(seconds: expiresIn));

    await _write(_accessTokenKey, accessToken);
    if (refreshToken != null) {
      await _write(_refreshTokenKey, refreshToken);
    }
    await _write(_tokenExpiryKey, expiry.toIso8601String());

    _cachedAccessToken = accessToken;
    _cachedTokenExpiry = expiry;
  }

  static Future<void> logout() async {
    try {
      final token =
          _cachedAccessToken ?? await _read(_accessTokenKey);
      if (token != null) {
        await http
            .post(
              Uri.parse(ApiConfig.authRevoke),
              headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer $token',
              },
            )
            .timeout(const Duration(seconds: 5));
      }
    } catch (e) {
      // Ignore errors during logout
    }

    await _delete(_accessTokenKey);
    await _delete(_refreshTokenKey);
    await _delete(_tokenExpiryKey);

    _cachedAccessToken = null;
    _cachedTokenExpiry = null;
  }

  static Future<Map<String, String>> getAuthHeaders() async {
    final token = await getAccessToken();

    if (token != null) {
      return {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      };
    }

    return {'Content-Type': 'application/json'};
  }

  static Future<http.Response> authenticatedRequest(
    String method,
    String path, {
    Map<String, dynamic>? body,
    Duration timeout = const Duration(seconds: 10),
  }) async {
    final headers = await getAuthHeaders();
    final uri = Uri.parse('${ApiConfig.baseUrl}$path');

    Map<String, dynamic>? requestBody = body;
    if (!headers.containsKey('Authorization') && body != null) {
      requestBody = Map<String, dynamic>.from(body);
      requestBody['deviceId'] = await getDeviceId();
    }

    http.Response response;

    switch (method.toUpperCase()) {
      case 'GET':
        response = await http.get(uri, headers: headers).timeout(timeout);
        break;
      case 'POST':
        response = await http
            .post(
              uri,
              headers: headers,
              body: requestBody != null ? json.encode(requestBody) : null,
            )
            .timeout(timeout);
        break;
      case 'PUT':
        response = await http
            .put(
              uri,
              headers: headers,
              body: requestBody != null ? json.encode(requestBody) : null,
            )
            .timeout(timeout);
        break;
      case 'DELETE':
        response = await http.delete(uri, headers: headers).timeout(timeout);
        break;
      default:
        throw ArgumentError('Unsupported HTTP method: $method');
    }

    if (response.statusCode == 401) {
      final refreshed = await refreshToken();
      if (refreshed) {
        return authenticatedRequest(method, path, body: body, timeout: timeout);
      }
    }

    return response;
  }
}
