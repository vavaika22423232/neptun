import 'package:flutter/foundation.dart';
import 'package:sentry_flutter/sentry_flutter.dart';

import '../utils/app_debug_log.dart';

/// Centralized error reporting via Sentry with local fallback.
class ErrorHandler {
  static bool _initAttempted = false;
  static bool _sentryReady = false;

  static Future<void> initialize({required String dsn}) async {
    if (_initAttempted) return;
    _initAttempted = true;

    if (dsn.isEmpty) {
      appTaggedLog('[ErrorHandler] Sentry skipped (empty DSN)', name: 'errors');
      return;
    }

    await SentryFlutter.init((options) {
      options.dsn = dsn;
      options.tracesSampleRate = 0.2;
      options.enableAutoPerformanceTracing = true;
      options.attachScreenshot = true;
      options.environment = kDebugMode ? 'development' : 'production';
      // Drop known webview_flutter_wkwebview Pigeon null-assertion noise (iOS edge cases)
      options.beforeSend = (event, hint) {
        final combined = '${event.throwable}${event.message}${event.throwable?.stackTrace}';
        if (combined.contains('web_kit.g.dart')) return null;
        return event;
      };
    });
    _sentryReady = true;
  }

  /// Call when Sentry was initialized via SentryFlutter.init in main().
  static void markInitialized() {
    _initAttempted = true;
    _sentryReady = true;
  }

  static void captureException(
    dynamic exception, {
    StackTrace? stackTrace,
    String? context,
    Map<String, dynamic>? extras,
  }) {
    appTaggedLog('[ErrorHandler] $context: $exception', name: 'errors');

    if (!_sentryReady || kDebugMode) {
      if (kDebugMode && stackTrace != null) {
        debugPrintStack(stackTrace: stackTrace);
      }
      return;
    }

    Sentry.captureException(
      exception,
      stackTrace: stackTrace,
      withScope: (scope) {
        if (context != null) scope.setTag('context', context);
        if (extras != null) {
          scope.setContexts('extras', extras);
        }
      },
    );
  }

  static void captureMessage(
    String message, {
    SentryLevel level = SentryLevel.info,
  }) {
    appTaggedLog('[ErrorHandler] $message', name: 'errors');
    if (!_sentryReady || kDebugMode) return;
    Sentry.captureMessage(message, level: level);
  }

  static void addBreadcrumb(String message, {String? category}) {
    if (!_sentryReady) return;
    Sentry.addBreadcrumb(Breadcrumb(
      message: message,
      category: category,
      timestamp: DateTime.now(),
    ));
  }

  static void setUserContext({String? id, String? nickname}) {
    if (!_sentryReady) return;
    Sentry.configureScope((scope) {
      scope.setUser(SentryUser(id: id, username: nickname));
    });
  }
}

/// Повертає зрозуміле користувачу повідомлення для типових мережевих/API помилок.
String userFriendlyErrorMessage(dynamic error) {
  if (error == null) return 'Щось пішло не так';
  final s = error.toString().toLowerCase();
  if (s.contains('timeout') || s.contains('timed out')) {
    return 'Час очікування вийшов. Перевірте з\'єднання і спробуйте знову.';
  }
  if (s.contains('socket') || s.contains('connection') || s.contains('network') ||
      s.contains('host') || s.contains('unreachable') || s.contains('failed host')) {
    return 'Немає з\'єднання з інтернетом. Перевірте мережу.';
  }
  if (s.contains('ssl') || s.contains('certificate')) {
    return 'Помилка безпечного з\'єднання. Спробуйте пізніше.';
  }
  return 'Щось пішло не так. Спробуйте пізніше.';
}

/// Result type for explicit error handling instead of try-catch everywhere.
sealed class Result<T> {
  const Result();
}

class Success<T> extends Result<T> {
  final T data;
  const Success(this.data);
}

class Failure<T> extends Result<T> {
  final String message;
  final dynamic error;
  const Failure(this.message, [this.error]);
}
