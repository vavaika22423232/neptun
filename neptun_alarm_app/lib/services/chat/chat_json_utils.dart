import 'dart:convert';

/// Parse online count from JSON (int, double, or String).
int parseChatOnlineCount(dynamic v) {
  if (v == null) return -1;
  if (v is int) return v >= 0 ? v : -1;
  if (v is double) return v >= 0 ? v.toInt() : -1;
  if (v is String) {
    final n = int.tryParse(v);
    return n != null && n >= 0 ? n : -1;
  }
  return -1;
}

/// Safe JSON decode — returns null if body is HTML or invalid object.
Map<String, dynamic>? tryDecodeJsonObject(String body) {
  final trimmed = body.trim();
  if (trimmed.isEmpty) return null;
  if (!trimmed.startsWith('{') && !trimmed.startsWith('[')) return null;
  try {
    final decoded = json.decode(body);
    return decoded is Map<String, dynamic> ? decoded : null;
  } catch (_) {
    return null;
  }
}
