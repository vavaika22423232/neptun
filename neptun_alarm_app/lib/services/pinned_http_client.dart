import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:http/io_client.dart';

/// Stub TLS client (certificate pinning to be re-enabled when [badCertificateCallback]
/// is wired to real SPKI checks). Prefer default [http.Client] for production
/// until pinning is fully implemented.
http.Client createPinnedHttpClient() {
  try {
    final inner = HttpClient()
      ..badCertificateCallback = (X509Certificate cert, String host, int port) {
        if (!host.contains('neptun.in.ua')) return false;
        return false;
      };
    return IOClient(inner);
  } catch (_) {
    return http.Client();
  }
}
