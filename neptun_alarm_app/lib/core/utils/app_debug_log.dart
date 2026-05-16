import 'package:flutter/foundation.dart';

/// Debug-only: `[tag] message` — second part optional.
void appDebugLog(String tag, [Object? message]) {
  if (kDebugMode) {
    debugPrint('[$tag] ${message ?? ''}');
  }
}

/// Debug-only message with bracket label ([name]/[tag]).
void appTaggedLog(Object message, {String? name, String? tag}) {
  if (!kDebugMode) return;
  final label = tag ?? name;
  debugPrint('[${label ?? 'app'}] $message');
}
