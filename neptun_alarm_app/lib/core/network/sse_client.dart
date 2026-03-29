import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

/// Reconnecting SSE client with exponential backoff and event parsing.
class SSEClient {
  http.Client? _client;
  StreamSubscription? _subscription;
  Timer? _keepaliveTimer;
  Timer? _reconnectTimer;

  bool _isConnected = false;
  bool _shouldReconnect = true;
  int _retryCount = 0;

  static const _minRetryDelay = Duration(seconds: 1);
  static const _maxRetryDelay = Duration(seconds: 30);
  static const _keepaliveTimeout = Duration(seconds: 50);

  final _eventController = StreamController<SSEEvent>.broadcast();
  final _connectionController = StreamController<bool>.broadcast();

  Stream<SSEEvent> get eventStream => _eventController.stream;
  Stream<bool> get connectionStream => _connectionController.stream;
  bool get isConnected => _isConnected;

  Future<void> connect(String url) async {
    _shouldReconnect = true;
    _retryCount = 0;
    await _doConnect(url);
  }

  Future<void> _doConnect(String url) async {
    _cleanup();
    _client = http.Client();

    try {
      final request = http.Request('GET', Uri.parse(url));
      request.headers['Accept'] = 'text/event-stream';
      request.headers['Cache-Control'] = 'no-cache';

      final response = await _client!.send(request);

      if (response.statusCode != 200) {
        debugPrint('SSE connection failed: ${response.statusCode}');
        _scheduleReconnect(url);
        return;
      }

      _isConnected = true;
      _retryCount = 0;
      _connectionController.add(true);
      _resetKeepalive(url);

      String buffer = '';
      _subscription = response.stream
          .transform(utf8.decoder)
          .listen(
            (chunk) {
              _resetKeepalive(url);
              buffer += chunk;

              while (buffer.contains('\n\n')) {
                final idx = buffer.indexOf('\n\n');
                final rawEvent = buffer.substring(0, idx);
                buffer = buffer.substring(idx + 2);
                _parseEvent(rawEvent);
              }
            },
            onError: (e) {
              debugPrint('SSE stream error: $e');
              _onDisconnect(url);
            },
            onDone: () => _onDisconnect(url),
            cancelOnError: false,
          );
    } catch (e) {
      debugPrint('SSE connect error: $e');
      _scheduleReconnect(url);
    }
  }

  void _parseEvent(String raw) {
    String? event;
    String? data;
    String? id;

    for (final line in raw.split('\n')) {
      if (line.startsWith('event:')) {
        event = line.substring(6).trim();
      } else if (line.startsWith('data:')) {
        data = line.substring(5).trim();
      } else if (line.startsWith('id:')) {
        id = line.substring(3).trim();
      }
    }

    if (data != null) {
      _eventController.add(SSEEvent(
        event: event ?? 'message',
        data: data,
        id: id,
      ));
    }
  }

  void _resetKeepalive(String url) {
    _keepaliveTimer?.cancel();
    _keepaliveTimer = Timer(_keepaliveTimeout, () {
      debugPrint('SSE keepalive timeout');
      _onDisconnect(url);
    });
  }

  void _onDisconnect(String url) {
    _isConnected = false;
    _connectionController.add(false);
    _scheduleReconnect(url);
  }

  void _scheduleReconnect(String url) {
    if (!_shouldReconnect) return;

    final delay = Duration(
      milliseconds: (_minRetryDelay.inMilliseconds *
              (1 << _retryCount.clamp(0, 5)))
          .clamp(
        _minRetryDelay.inMilliseconds,
        _maxRetryDelay.inMilliseconds,
      ),
    );

    _retryCount++;
    debugPrint('SSE reconnect in ${delay.inSeconds}s (attempt $_retryCount)');

    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(delay, () => _doConnect(url));
  }

  void _cleanup() {
    _subscription?.cancel();
    _subscription = null;
    _keepaliveTimer?.cancel();
    _reconnectTimer?.cancel();
    _client?.close();
    _client = null;
    _isConnected = false;
  }

  void disconnect() {
    _shouldReconnect = false;
    _cleanup();
    _connectionController.add(false);
  }

  void dispose() {
    disconnect();
    _eventController.close();
    _connectionController.close();
  }
}

class SSEEvent {
  final String event;
  final String data;
  final String? id;

  const SSEEvent({
    required this.event,
    required this.data,
    this.id,
  });

  Map<String, dynamic>? get json {
    try {
      return jsonDecode(data) as Map<String, dynamic>;
    } catch (_) {
      return null;
    }
  }
}
