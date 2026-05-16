import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../config/api_config.dart';
import '../features/map/domain/map_realtime_link_status.dart';

/// Singleton SSE hub — ONE connection for ALL real-time events.
///
/// The server multiplexes:
///   - `alarm_update`   — full alarm data when alarms change
///   - `marker_new`     — new threat marker from worker ingest
///   - `markers_refresh`— bulk queue replay / batch ingest (triggers full refetch)
///   - `marker_update`  — partial update for existing marker (position etc)
///   - `marker_delete`  — marker removed (admin delete)
///   - `track_update`   — position delta for tracked threat (shahed/missile moving)
///   - `connected`      — initial online count on connect
///   - `online`         — online count updates
///   - `new_message`    — new chat message
///   - `delete_message` — chat message deleted
///   - `reaction`       — chat reaction toggled
///   - `typing`         — typing indicator update
///
/// ChatService subscribes to chat streams instead of opening its own SSE.
class DataStreamService {
  DataStreamService._();
  static final DataStreamService instance = DataStreamService._();

  // ── Alarm & marker streams ─────────────────────────────────────────────
  final _alarmController = StreamController<List<dynamic>>.broadcast();
  final _markerNewController =
      StreamController<Map<String, dynamic>>.broadcast();
  final _trackUpdateController =
      StreamController<Map<String, dynamic>>.broadcast();
  final _markerUpdateController =
      StreamController<Map<String, dynamic>>.broadcast();
  final _markerDeleteController = StreamController<String>.broadcast();

  Stream<List<dynamic>> get alarmStream => _alarmController.stream;
  Stream<Map<String, dynamic>> get markerNewStream =>
      _markerNewController.stream;
  /// Position/track delta updates — apply in-place, no full refetch.
  Stream<Map<String, dynamic>> get trackUpdateStream =>
      _trackUpdateController.stream;
  /// Partial marker field updates (legacy, non-track markers).
  Stream<Map<String, dynamic>> get markerUpdateStream =>
      _markerUpdateController.stream;
  /// Marker removed (admin delete).
  Stream<String> get markerDeleteStream => _markerDeleteController.stream;

  // ── Chat streams (consumed by ChatService) ─────────────────────────────
  final _chatNewMessageController =
      StreamController<Map<String, dynamic>>.broadcast();
  final _chatDeleteController =
      StreamController<Map<String, dynamic>>.broadcast();
  final _chatReactionController =
      StreamController<Map<String, dynamic>>.broadcast();
  final _chatEditController =
      StreamController<Map<String, dynamic>>.broadcast();
  final _chatTypingController =
      StreamController<Map<String, dynamic>>.broadcast();
  final _chatOnlineController = StreamController<int>.broadcast();

  Stream<Map<String, dynamic>> get chatNewMessageStream =>
      _chatNewMessageController.stream;
  Stream<Map<String, dynamic>> get chatDeleteStream =>
      _chatDeleteController.stream;
  Stream<Map<String, dynamic>> get chatReactionStream =>
      _chatReactionController.stream;
  Stream<Map<String, dynamic>> get chatEditStream =>
      _chatEditController.stream;
  Stream<Map<String, dynamic>> get chatTypingStream =>
      _chatTypingController.stream;
  Stream<int> get chatOnlineStream => _chatOnlineController.stream;

  /// Стан живого SSE для HUD карти («Ситуація зараз»).
  final ValueNotifier<MapRealtimeLinkStatus> mapRealtimeLink =
      ValueNotifier(MapRealtimeLinkStatus.initial);

  // ── SSE internals ──────────────────────────────────────────────────────
  http.Client? _sseClient;
  StreamSubscription? _sseSubscription;
  Timer? _reconnectTimer;
  Timer? _keepaliveTimer;
  int _reconnectDelay = 1;
  bool _connected = false;
  bool _disposed = false;

  void _notifyMapReconnectingPhase() {
    mapRealtimeLink.value = mapRealtimeLink.value.copyWith(
      phase: MapRealtimeLinkPhase.reconnecting,
    );
  }

  void _notifyMapConnectingPhase() {
    mapRealtimeLink.value = mapRealtimeLink.value.copyWith(
      phase: MapRealtimeLinkPhase.connecting,
    );
  }

  void _notifyMapLivePhase({bool bumpSignificant = false}) {
    final prev = mapRealtimeLink.value;
    mapRealtimeLink.value = prev.copyWith(
      phase: MapRealtimeLinkPhase.live,
      lastSignificantRefreshAt: bumpSignificant
          ? DateTime.now()
          : prev.lastSignificantRefreshAt,
    );
  }

  /// Для HUD не враховуємо високочастотні `track_update`.
  void _notifyMapSignificantRefresh() {
    _notifyMapLivePhase(bumpSignificant: true);
  }

  /// Start listening to SSE. Safe to call multiple times.
  void connect() {
    if (_connected || _disposed) return;
    _connected = true;
    _reconnectTimer?.cancel();
    _startSSE();
  }

  /// Force reconnect — call when app returns from background.
  /// Socket often killed by OS in background; keeps real-time data fresh.
  void forceReconnectIfNeeded() {
    if (_disposed) return;
    _reconnectDelay = 1;
    _connected = false;
    _reconnectTimer?.cancel();
    _keepaliveTimer?.cancel();
    _sseSubscription?.cancel();
    _sseSubscription = null;
    _sseClient?.close();
    _sseClient = null;
    connect();
  }

  void _startSSE() async {
    _notifyMapConnectingPhase();
    _sseSubscription?.cancel();
    _sseSubscription = null;
    _sseClient?.close();
    _sseClient = http.Client();

    try {
      final request = http.Request('GET', Uri.parse(ApiConfig.chatStream));
      request.headers['Accept'] = 'text/event-stream';
      request.headers['Cache-Control'] = 'no-cache';

      final response = await _sseClient!.send(request);

      if (response.statusCode != 200) {
        debugPrint('📡 DataStream SSE: HTTP ${response.statusCode}');
        _notifyMapReconnectingPhase();
        _scheduleReconnect();
        return;
      }

      _reconnectDelay = 1;
      _resetKeepaliveTimer();
      debugPrint('📡 DataStream SSE: connected');

      String buffer = '';
      _notifyMapLivePhase();

      _sseSubscription = response.stream
          .transform(utf8.decoder)
          .listen(
            (chunk) {
              if (_disposed) return;
              _resetKeepaliveTimer();
              buffer += chunk;

              while (buffer.contains('\n\n')) {
                final idx = buffer.indexOf('\n\n');
                final frame = buffer.substring(0, idx);
                buffer = buffer.substring(idx + 2);
                _processFrame(frame);
              }
            },
            onError: (error) {
              debugPrint('📡 DataStream SSE error: $error');
              _scheduleReconnect();
            },
            onDone: () {
              debugPrint('📡 DataStream SSE closed');
              _scheduleReconnect();
            },
            cancelOnError: false,
          );
    } catch (e) {
      debugPrint('📡 DataStream SSE connect error: $e');
      _notifyMapReconnectingPhase();
      _scheduleReconnect();
    }
  }

  static int _parseOnlineCount(dynamic v) {
    if (v == null) return 0;
    if (v is int) return v >= 0 ? v : 0;
    if (v is double) return v >= 0 ? v.toInt() : 0;
    if (v is String) {
      final n = int.tryParse(v);
      return n != null && n >= 0 ? n : 0;
    }
    return 0;
  }

  void _processFrame(String frame) {
    if (frame.trim().startsWith(':')) return; // keepalive

    String? eventType;
    final dataLines = <String>[];
    for (final line in frame.split('\n')) {
      if (line.startsWith('event:')) {
        eventType = line.substring(6).trim();
      } else if (line.startsWith('data:')) {
        dataLines.add(line.substring(5).trim());
      }
    }
    if (dataLines.isEmpty) return;

    final raw = dataLines.join('\n').trim();
    if (raw.startsWith('<')) return; // HTML error page, not JSON

    try {
      final data = json.decode(raw);

      // Handle wrapper format: { type, data } or direct event
      String type;
      dynamic payload;

      if (data is Map<String, dynamic> && data.containsKey('type')) {
        type = data['type']?.toString() ?? eventType ?? '';
        payload = data['data'];
      } else {
        type = eventType ?? '';
        payload = data;
      }

      switch (type) {
        // ── Map / alarm events ───────────────────────────────────────────
        case 'alarm_update':
          if (payload is List) {
            _notifyMapSignificantRefresh();
            _alarmController.add(payload);
          }
          break;

        case 'marker_new':
          if (payload is Map<String, dynamic>) {
            _notifyMapSignificantRefresh();
            _markerNewController.add(payload);
          }
          break;

        case 'markers_refresh':
          // Same listeners as marker_new — map page refetches /api/threats (full list).
          _notifyMapSignificantRefresh();
          _markerNewController.add(<String, dynamic>{
            '_markersRefresh': true,
            if (payload is Map<String, dynamic>) ...payload,
          });
          break;

        case 'marker_update':
          if (payload is Map<String, dynamic> && payload['id'] != null) {
            _notifyMapSignificantRefresh();
            _markerUpdateController.add(payload);
          }
          break;

        case 'marker_delete':
          if (payload is Map<String, dynamic>) {
            final id = payload['id']?.toString();
            if (id != null && id.isNotEmpty) {
              _notifyMapSignificantRefresh();
              _markerDeleteController.add(id);
            }
          }
          break;

        case 'track_update':
          if (payload is Map<String, dynamic> &&
              payload['marker'] is Map<String, dynamic>) {
            _trackUpdateController.add(payload);
          }
          break;

        // ── Chat events ──────────────────────────────────────────────────
        case 'connected':
        case 'online':
          if (payload is Map<String, dynamic>) {
            final count = _parseOnlineCount(payload['online']);
            _chatOnlineController.add(count);
          }
          break;

        case 'new_message':
          if (payload is Map<String, dynamic>) {
            _chatNewMessageController.add(payload);
          }
          break;

        case 'delete_message':
          if (payload is Map<String, dynamic>) {
            _chatDeleteController.add(payload);
          }
          break;

        case 'reaction':
          if (payload is Map<String, dynamic>) {
            _chatReactionController.add(payload);
          }
          break;

        case 'edit_message':
          if (payload is Map<String, dynamic>) {
            _chatEditController.add(payload);
          }
          break;

        case 'typing':
          if (payload is Map<String, dynamic>) {
            _chatTypingController.add(payload);
          }
          break;
      }
    } catch (e) {
      debugPrint('📡 DataStream parse error: $e');
    }
  }

  void _resetKeepaliveTimer() {
    _keepaliveTimer?.cancel();
    _keepaliveTimer = Timer(const Duration(seconds: 50), () {
      debugPrint('📡 DataStream: no keepalive, reconnecting');
      _scheduleReconnect();
    });
  }

  void _scheduleReconnect() {
    _notifyMapReconnectingPhase();
    _connected = false;
    _sseSubscription?.cancel();
    _sseSubscription = null;
    _sseClient?.close();
    _sseClient = null;
    _keepaliveTimer?.cancel();

    if (_disposed) return;

    final delay = _reconnectDelay;
    _reconnectDelay = (_reconnectDelay * 2).clamp(1, 30);

    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(Duration(seconds: delay), () {
      if (!_disposed) {
        _connected = false;
        connect();
      }
    });
  }

  void disconnect() {
    _connected = false;
    _reconnectTimer?.cancel();
    _keepaliveTimer?.cancel();
    _sseSubscription?.cancel();
    _sseSubscription = null;
    _sseClient?.close();
    _sseClient = null;
  }

  void dispose() {
    _disposed = true;
    disconnect();
    _alarmController.close();
    _markerNewController.close();
    _trackUpdateController.close();
    _markerUpdateController.close();
    _markerDeleteController.close();
    _chatNewMessageController.close();
    _chatDeleteController.close();
    _chatReactionController.close();
    _chatEditController.close();
    _chatTypingController.close();
    _chatOnlineController.close();
  }
}
