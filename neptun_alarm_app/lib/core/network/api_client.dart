import 'dart:convert';
import 'dart:async';
import 'package:http/http.dart' as http;
import '../../config/config.dart';

/// Centralized HTTP client with error handling, timeouts, and retry logic.
class ApiClient {
  final http.Client _client = http.Client();

  static bool _isTransientFailure(ApiResponse r) {
    if (r.statusCode == 408 || r.statusCode == 429) return true;
    if (r.statusCode >= 500 && r.statusCode < 600) return true;
    if (r.statusCode == 0 && (r.error ?? '').isNotEmpty) return true;
    return false;
  }

  Future<ApiResponse> _getOnce(
    String url, {
    Map<String, String>? headers,
    Duration? timeout,
  }) async {
    try {
      final response = await _client
          .get(Uri.parse(url), headers: headers)
          .timeout(timeout ?? ApiConfig.httpTimeout);
      return ApiResponse(
        statusCode: response.statusCode,
        body: response.body,
        isSuccess: response.statusCode >= 200 && response.statusCode < 300,
      );
    } on TimeoutException {
      return ApiResponse(statusCode: 408, body: '', error: 'Request timeout');
    } catch (e) {
      return ApiResponse(statusCode: 0, body: '', error: e.toString());
    }
  }

  /// [maxRetries] — extra attempts after the first (e.g. 2 → up to 3 tries) on 5xx / timeout / network.
  Future<ApiResponse> get(
    String url, {
    Map<String, String>? headers,
    Duration? timeout,
    int maxRetries = 2,
  }) async {
    final attempts = maxRetries + 1;
    ApiResponse? last;
    for (var i = 0; i < attempts; i++) {
      last = await _getOnce(url, headers: headers, timeout: timeout);
      if (last.isSuccess || !_isTransientFailure(last) || i == attempts - 1) {
        return last;
      }
      await Future<void>.delayed(Duration(milliseconds: 350 * (1 << i)));
    }
    return last!;
  }

  Future<ApiResponse> post(
    String url, {
    Map<String, String>? headers,
    Object? body,
    Duration? timeout,
  }) async {
    try {
      final response = await _client
          .post(
            Uri.parse(url),
            headers: {
              'Content-Type': 'application/json',
              ...?headers,
            },
            body: body is String ? body : jsonEncode(body),
          )
          .timeout(timeout ?? ApiConfig.httpTimeout);
      return ApiResponse(
        statusCode: response.statusCode,
        body: response.body,
        isSuccess: response.statusCode >= 200 && response.statusCode < 300,
      );
    } on TimeoutException {
      return ApiResponse(statusCode: 408, body: '', error: 'Request timeout');
    } catch (e) {
      return ApiResponse(statusCode: 0, body: '', error: e.toString());
    }
  }

  Future<ApiResponse> delete(
    String url, {
    Map<String, String>? headers,
    Duration? timeout,
  }) async {
    try {
      final response = await _client
          .delete(Uri.parse(url), headers: headers)
          .timeout(timeout ?? ApiConfig.httpTimeout);
      return ApiResponse(
        statusCode: response.statusCode,
        body: response.body,
        isSuccess: response.statusCode >= 200 && response.statusCode < 300,
      );
    } on TimeoutException {
      return ApiResponse(statusCode: 408, body: '', error: 'Request timeout');
    } catch (e) {
      return ApiResponse(statusCode: 0, body: '', error: e.toString());
    }
  }

  void dispose() {
    _client.close();
  }
}

class ApiResponse {
  final int statusCode;
  final String body;
  final bool isSuccess;
  final String? error;

  const ApiResponse({
    required this.statusCode,
    required this.body,
    this.isSuccess = false,
    this.error,
  });

  Map<String, dynamic>? get json {
    final trimmed = body.trim();
    if (trimmed.isEmpty || !trimmed.startsWith('{')) return null;
    try {
      return jsonDecode(body) as Map<String, dynamic>;
    } catch (_) {
      return null;
    }
  }

  List<dynamic>? get jsonList {
    final trimmed = body.trim();
    if (trimmed.isEmpty || !trimmed.startsWith('[')) return null;
    try {
      return jsonDecode(body) as List<dynamic>;
    } catch (_) {
      return null;
    }
  }
}
