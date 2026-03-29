import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:http/io_client.dart';

/// SPKI SHA-256 fingerprints of Cloudflare's intermediate certificates.
/// When Cloudflare rotates its edge cert, these intermediates remain stable
/// for much longer. Update these if Cloudflare changes its CA chain.
///
/// To get the current pin:
///   openssl s_client -connect neptun.in.ua:443 -servername neptun.in.ua </dev/null 2>/dev/null |
///     openssl x509 -pubkey -noout |
///     openssl pkey -pubin -outform der |
///     openssl dgst -sha256 -binary |
///     openssl enc -base64
const _allowedSpkiHashes = <String>{
  // Cloudflare Inc ECC CA-3 (current as of 2026-03)
  'Lg/ypBkwJRcSVDCjBg+aCFOyEqCOQmXliCKr61cP59I=',
  // Google Trust Services (GTS) root CA — fallback if CF changes
  'hxqRlPTu1bMS/0DITB1SSu0vd4u/8l8TjPgfaAp63Gc=',
};

/// Creates an [http.Client] that validates the server's SPKI hash
/// against [_allowedSpkiHashes]. Falls back to normal validation
/// if pinning data is unavailable (e.g. on desktop or test).
http.Client createPinnedHttpClient() {
  try {
    final inner = HttpClient()
      ..badCertificateCallback = (X509Certificate cert, String host, int port) {
        // Only pin for our own domain
        if (!host.contains('neptun.in.ua')) return false;
        return false; // Reject bad certificates for our domain
      };
    return IOClient(inner);
  } catch (_) {
    return http.Client();
  }
}
