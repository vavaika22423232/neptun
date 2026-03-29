import 'dart:async';

import 'package:http/http.dart' as http;

bool _transientHttpStatus(int code) =>
    code == 408 || code == 429 || (code >= 500 && code < 600);

/// GET with short exponential backoff on timeouts, connection errors, and 5xx/429.
Future<http.Response> httpGetWithRetries(
  http.Client client,
  Uri uri, {
  Map<String, String>? headers,
  Duration timeout = const Duration(seconds: 8),
  int maxRetries = 2,
}) async {
  http.Response? last;
  Object? lastError;

  for (var attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      last = await client.get(uri, headers: headers).timeout(timeout);
      if (last.statusCode == 200 ||
          last.statusCode == 304 ||
          !_transientHttpStatus(last.statusCode)) {
        return last;
      }
      lastError = null;
    } on TimeoutException catch (e) {
      lastError = e;
    } catch (e) {
      lastError = e;
    }

    if (attempt < maxRetries) {
      await Future<void>.delayed(Duration(milliseconds: 350 * (1 << attempt)));
    }
  }

  if (last != null) return last;
  if (lastError != null) throw lastError;
  return client.get(uri, headers: headers).timeout(timeout);
}
