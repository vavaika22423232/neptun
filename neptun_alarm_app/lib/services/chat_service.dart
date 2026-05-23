import 'dart:async';
import 'dart:convert';
import 'dart:io' show Platform;
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:android_id/android_id.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';
import '../config/api_config.dart';
import '../config/prefs_keys.dart';
import '../models/chat_message.dart';
import 'auth_service.dart';
import 'moderator_service.dart';
import 'purchase_service.dart';
import 'data_stream_service.dart';
import 'package:path_provider/path_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:neptun_alarm_app/core/utils/app_debug_log.dart';
import 'package:neptun_alarm_app/core/utils/connectivity_utils.dart';

/// Ban entry with reason and metadata.
class BanEntry {
  final String nickname;
  final String reason;
  final String? bannedAt;
  final String? bannedBy;

  const BanEntry({
    required this.nickname,
    required this.reason,
    this.bannedAt,
    this.bannedBy,
  });
}

/// Singleton chat service: REST API calls + real-time via DataStreamService SSE.
/// NO own SSE connection — subscribes to DataStreamService singleton instead.
class ChatService {
  ChatService._();
  static final ChatService instance = ChatService._();

  // ── State ──────────────────────────────────────────────────────────────
  String? _deviceId;
  String? _nickname;
  String? _hardwareId; // Android ID — survives app reinstall
  bool _isModerator = false;
  bool _isBanned = false;
  String? _banReason;
  int _onlineCount = 0;

  StreamSubscription<List<ConnectivityResult>>? _connectivitySubscription;
  StreamSubscription<bool>? _moderatorSubscription;

  String? get deviceId => _deviceId;
  String? get nickname => _nickname;
  bool get isModerator => _isModerator;
  bool get isBanned => _isBanned;
  String? get banReason => _banReason;
  int get onlineCount => _onlineCount;

  // ── Stream controllers ─────────────────────────────────────────────────
  final _messagesController = StreamController<List<ChatMessage>>.broadcast();
  final _newMessageController = StreamController<ChatMessage>.broadcast();
  final _deleteController = StreamController<String>.broadcast();
  final _reactionController =
      StreamController<
        ({String messageId, Map<String, List<ReactionInfo>> reactions})
      >.broadcast();
  final _editController = StreamController<ChatMessage>.broadcast();
  final _typingController = StreamController<List<String>>.broadcast();
  final _onlineController = StreamController<int>.broadcast();
  final _banStatusController = StreamController<bool>.broadcast();
  final _errorController = StreamController<String>.broadcast();

  Stream<List<ChatMessage>> get messagesStream => _messagesController.stream;
  Stream<ChatMessage> get newMessageStream => _newMessageController.stream;
  Stream<String> get deleteStream => _deleteController.stream;
  Stream<({String messageId, Map<String, List<ReactionInfo>> reactions})>
  get reactionStream => _reactionController.stream;
  Stream<ChatMessage> get editStream => _editController.stream;
  Stream<List<String>> get typingStream => _typingController.stream;
  Stream<int> get onlineStream => _onlineController.stream;
  Stream<bool> get banStatusStream => _banStatusController.stream;
  Stream<String> get errorStream => _errorController.stream;

  // ── Offline queue & pending status ────────────────────────────────────
  final _pendingIds = <String>{};
  final _pendingIdsController = StreamController<Set<String>>.broadcast();
  final _pendingResolvedController =
      StreamController<({String pendingId, ChatMessage message})>.broadcast();

  Stream<Set<String>> get pendingIdsStream => _pendingIdsController.stream;
  Stream<({String pendingId, ChatMessage message})> get pendingResolvedStream =>
      _pendingResolvedController.stream;

  bool isPending(String messageId) => _pendingIds.contains(messageId);

  void _addPending(String id) {
    _pendingIds.add(id);
    _pendingIdsController.add(Set.from(_pendingIds));
  }

  void _removePending(String id) {
    _pendingIds.remove(id);
    _pendingIdsController.add(Set.from(_pendingIds));
  }

  static const _offlineQueueKey = PrefsKeys.chatOfflineQueue;
  static const _maxOfflineQueue = 50;

  Future<List<Map<String, dynamic>>> getOfflineQueue() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_offlineQueueKey);
    if (raw == null) return [];
    try {
      final list = json.decode(raw) as List?;
      return list?.map((e) => Map<String, dynamic>.from(e as Map)).toList() ??
          [];
    } catch (_) {
      return [];
    }
  }

  Future<void> _saveOfflineQueue(List<Map<String, dynamic>> queue) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_offlineQueueKey, json.encode(queue));
  }

  Future<void> addToOfflineQueue({
    required String pendingId,
    required String text,
    String? replyToId,
  }) async {
    final queue = await getOfflineQueue();
    if (queue.length >= _maxOfflineQueue) return;
    queue.add({'pendingId': pendingId, 'text': text, 'replyToId': replyToId});
    await _saveOfflineQueue(queue);
    _addPending(pendingId);
  }

  Future<void> removeFirstFromOfflineQueue() async {
    final queue = await getOfflineQueue();
    if (queue.isEmpty) return;
    queue.removeAt(0);
    await _saveOfflineQueue(queue);
  }

  /// Restore _pendingIds from saved queue (call on app start).
  Future<void> restorePendingFromQueue() async {
    final queue = await getOfflineQueue();
    for (final item in queue) {
      final id = item['pendingId']?.toString();
      if (id != null && id.isNotEmpty) _pendingIds.add(id);
    }
    if (_pendingIds.isNotEmpty) {
      _pendingIdsController.add(Set.from(_pendingIds));
    }
  }

  /// Serialize flushes — [Connectivity] callbacks and chat [_init] can fire together;
  /// concurrent reads of the prefs queue duplicated [sendMessage] calls before removal.
  Future<void> _offlineFlushChain = Future.value();

  /// Flush offline queue: send each message, on success emit (pendingId, realMessage).
  Future<void> flushOfflineQueue() {
    _offlineFlushChain = _offlineFlushChain.then((_) async {
      try {
        await _flushOfflineQueueSerialized();
      } catch (e, st) {
        appDebugLog('❌ flushOfflineQueue: $e\n$st');
      }
    });
    return _offlineFlushChain;
  }

  Future<void> _flushOfflineQueueSerialized() async {
    if (_deviceId == null || _nickname == null) return;
    var queue = await getOfflineQueue();
    if (queue.isEmpty) return;

    while (queue.isNotEmpty) {
      final item = queue.first;
      final pendingId = item['pendingId']?.toString() ?? '';
      final text = item['text']?.toString() ?? '';
      final replyToId = item['replyToId']?.toString();

      final sent = await sendMessage(text, replyToId: replyToId);
      if (sent != null) {
        await removeFirstFromOfflineQueue();
        _removePending(pendingId);
        _pendingResolvedController.add((pendingId: pendingId, message: sent));
        queue = await getOfflineQueue();
      } else {
        break;
      }
    }
  }

  // ── SSE subscriptions (from DataStreamService) ─────────────────────────
  final _sseSubscriptions = <StreamSubscription>[];
  bool _sseListening = false;
  bool _disposed = false;

  // ── Dedup: track recent message IDs to prevent duplicates ──────────────
  final _recentMessageIds = <String>{};
  static const _maxRecentIds = 300;

  /// Parse online count from JSON (int, double, or String).
  static int _parseOnline(dynamic v) {
    if (v == null) return -1;
    if (v is int) return v >= 0 ? v : -1;
    if (v is double) return v >= 0 ? v.toInt() : -1;
    if (v is String) {
      final n = int.tryParse(v);
      return n != null && n >= 0 ? n : -1;
    }
    return -1;
  }

  /// Safe JSON decode — returns null if body is HTML or invalid.
  static Map<String, dynamic>? _tryDecodeJson(String body) {
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

  // ── Rate limiter ───────────────────────────────────────────────────────
  DateTime? _lastSendTime;
  static const _rateLimitMs = 3000;

  /// Maximum chat message length (aligned with API); use the same value in input UI.
  static const int maxMessageLength = 500;

  // ── Initialization ─────────────────────────────────────────────────────
  Future<void> init() async {
    await _connectivitySubscription?.cancel();
    await _moderatorSubscription?.cancel();
    _connectivitySubscription = null;
    _moderatorSubscription = null;

    final prefs = await SharedPreferences.getInstance();
    _deviceId = await AuthService.getDeviceId();
    _nickname = prefs.getString('chat_nickname');
    if (!kIsWeb && Platform.isAndroid) {
      try {
        final id = await const AndroidId().getId();
        if (id != null && id.isNotEmpty) _hardwareId = id;
      } catch (_) {}
    }
    // Sync moderator state from ModeratorService
    _isModerator = ModeratorService.instance.isModerator;
    // Listen for moderator state changes (init() may run multiple times — replace subscription)
    _moderatorSubscription = ModeratorService.instance.stream.listen((isMod) {
      _isModerator = isMod;
    });
    // Load block list so isBlocked works before chat opens
    await loadBlockList();
    // Check ban in background
    unawaited(checkBanStatus());
    // Flush offline queue when connectivity restored (works even when chat tab not open)
    _connectivitySubscription = Connectivity().onConnectivityChanged.listen((
      results,
    ) async {
      if (connectivityResultsOnline(results)) await flushOfflineQueue();
    });
  }

  Future<Map<String, String>> _authHeaders() async {
    return AuthService.getAuthHeaders();
  }

  /// Multipart must not set Content-Type (boundary); only attach Bearer.
  Future<void> _attachBearerToMultipart(http.MultipartRequest request) async {
    await _ensureToken();
    final token = await AuthService.getAccessToken();
    if (token != null && token.isNotEmpty) {
      request.headers['Authorization'] = 'Bearer $token';
    }
  }

  Future<void> _ensureToken() async {
    final hasToken = await AuthService.hasValidToken();
    if (!hasToken) {
      await AuthService.login(nickname: _nickname);
    }
  }

  /// First page size (smaller = faster JSON parse + first paint; history via pagination).
  static const int _initialFetchLimit = 50;

  // ── REST: Fetch messages ───────────────────────────────────────────────
  Future<List<ChatMessage>> fetchMessages({int? before, int limit = 50}) async {
    try {
      await _ensureToken();
      var url = ApiConfig.chatMessages;
      if (before != null) {
        url = '$url?before=$before&limit=$limit';
      } else {
        url = '$url?limit=$_initialFetchLimit';
      }
      final headers = await _authHeaders();
      final resp = await http
          .get(Uri.parse(url), headers: headers)
          .timeout(ApiConfig.httpTimeout);
      if (resp.statusCode == 200) {
        final data = _tryDecodeJson(resp.body);
        if (data == null) {
          appDebugLog('❌ fetchMessages: invalid response (HTML?)');
          return [];
        }
        final raw = (data['messages'] as List?) ?? [];
        // Fallback: use fetch's "recently active" count until SSE delivers real-time count.
        // SSE 'connected' and 'online' events will overwrite with correct value.
        final fetchOnline = _parseOnline(data['online']);
        if (fetchOnline >= 0) {
          _onlineCount = fetchOnline;
          _onlineController.add(_onlineCount);
        }
        final messages = raw
            .map((j) => ChatMessage.fromJson(j as Map<String, dynamic>))
            .toList()
            .reversed
            .toList();
        if (before == null) {
          _recentMessageIds.clear();
          _messagesController.add(messages);
        }
        for (final m in messages) {
          _recentMessageIds.add(m.id);
        }
        return messages;
      }
    } catch (e) {
      appDebugLog('❌ fetchMessages error: $e');
      _errorController.add('Помилка завантаження повідомлень');
    }
    return [];
  }

  /// Fetches older messages for pagination. Returns messages older than [beforeTimestamp].
  Future<List<ChatMessage>> fetchMoreMessages(int beforeTimestamp) async {
    return fetchMessages(before: beforeTimestamp, limit: 50);
  }

  /// Остання сторінка через REST без скидання dedup-пулу SSE і без broadcast у [messagesStream] —
  /// добір повідомлень, які могли прийти під час паузи / розриву каналу.
  Future<List<ChatMessage>> peekLatestMessagesTail({int limit = 50}) async {
    try {
      if (_deviceId == null || _nickname == null) return [];
      await _ensureToken();
      final safeLimit = limit.clamp(1, 100);
      final headers = await _authHeaders();
      final resp = await http
          .get(
            Uri.parse('${ApiConfig.chatMessages}?limit=$safeLimit'),
            headers: headers,
          )
          .timeout(ApiConfig.httpTimeout);
      if (resp.statusCode != 200) return [];
      final data = _tryDecodeJson(resp.body);
      if (data == null) return [];
      final raw = (data['messages'] as List?) ?? [];
      final fetchOnline = _parseOnline(data['online']);
      if (fetchOnline >= 0) {
        _onlineCount = fetchOnline;
        _onlineController.add(_onlineCount);
      }
      return raw
          .map((j) => ChatMessage.fromJson(j as Map<String, dynamic>))
          .toList()
          .reversed
          .toList();
    } catch (e) {
      appDebugLog('❌ peekLatestMessagesTail error: $e');
      return [];
    }
  }

  /// Після добору історії REST — щоб [connectSSE] не дублював ті самі id.
  void ingestSeenMessageIdsForSseDedup(Iterable<String> ids) {
    for (final id in ids) {
      final trimmed = id.trim();
      if (trimmed.isEmpty) continue;
      if (_recentMessageIds.contains(trimmed)) continue;
      _recentMessageIds.add(trimmed);
      while (_recentMessageIds.length > _maxRecentIds) {
        _recentMessageIds.remove(_recentMessageIds.first);
      }
    }
  }

  // ── REST: Send message ─────────────────────────────────────────────────
  Future<ChatMessage?> sendMessage(String text, {String? replyToId}) async {
    if (_deviceId == null || _nickname == null) return null;

    // Client-side rate limit
    if (_lastSendTime != null) {
      final diff = DateTime.now().difference(_lastSendTime!).inMilliseconds;
      if (diff < _rateLimitMs) {
        _errorController.add(
          'Зачекайте ${((_rateLimitMs - diff) / 1000).ceil()} сек',
        );
        return null;
      }
    }

    final trimmed = text.trim();
    if (trimmed.isEmpty) return null;
    if (trimmed.length > maxMessageLength) {
      _errorController.add(
        'Повідомлення занадто довге (макс $maxMessageLength)',
      );
      return null;
    }

    try {
      _lastSendTime = DateTime.now();
      await _ensureToken();
      final body = <String, dynamic>{
        'message': trimmed,
        'isPro': PurchaseService().isPremium,
      };
      if (replyToId != null) body['replyTo'] = replyToId;
      if (_hardwareId != null) body['hardwareId'] = _hardwareId;

      final headers = await _authHeaders();
      final resp = await http
          .post(
            Uri.parse(ApiConfig.chatSend),
            headers: headers,
            body: json.encode(body),
          )
          .timeout(ApiConfig.httpTimeout);

      final data = _tryDecodeJson(resp.body);
      if (data != null && resp.statusCode == 200 && data['message'] != null) {
        final msg = ChatMessage.fromJson(
          data['message'] as Map<String, dynamic>,
        );
        _recentMessageIds.add(msg.id);
        if (_recentMessageIds.length > _maxRecentIds) {
          _recentMessageIds.remove(_recentMessageIds.first);
        }
        return msg;
      }
      if (data != null && resp.statusCode == 403) {
        _isBanned = true;
        _banReason = data['error']?.toString();
        _banStatusController.add(true);
      }
      _errorController.add(data?['error']?.toString() ?? 'Помилка відправки');
    } catch (e) {
      appDebugLog('❌ sendMessage error: $e');
      _errorController.add('Помилка з\'єднання');
    }
    return null;
  }

  // ── REST: Send voice message ───────────────────────────────────────────
  Future<ChatMessage?> sendVoiceMessage(
    String filePath,
    int durationSeconds,
  ) async {
    if (_deviceId == null || _nickname == null) return null;
    if (!PurchaseService().isPremium) {
      _errorController.add('Голосові повідомлення доступні тільки з PRO');
      return null;
    }

    // Client-side rate limit
    if (_lastSendTime != null) {
      final diff = DateTime.now().difference(_lastSendTime!).inMilliseconds;
      if (diff < _rateLimitMs) {
        _errorController.add(
          'Зачекайте ${((_rateLimitMs - diff) / 1000).ceil()} сек',
        );
        return null;
      }
    }

    try {
      _lastSendTime = DateTime.now();

      final uri = Uri.parse(ApiConfig.chatUploadAudio);
      final request = http.MultipartRequest('POST', uri);
      request.fields['deviceId'] = _deviceId!;
      request.fields['nickname'] = _nickname!;
      request.fields['duration'] = durationSeconds.toString();
      request.fields['isPro'] = PurchaseService().isPremium.toString();
      if (_hardwareId != null) request.fields['hardwareId'] = _hardwareId!;
      request.files.add(await http.MultipartFile.fromPath('audio', filePath));

      await _attachBearerToMultipart(request);
      final streamed = await request.send().timeout(ApiConfig.longHttpTimeout);
      final resp = await http.Response.fromStream(streamed);

      final data = _tryDecodeJson(resp.body);
      if (data != null && resp.statusCode == 200 && data['message'] != null) {
        final msg = ChatMessage.fromJson(
          data['message'] as Map<String, dynamic>,
        );
        _recentMessageIds.add(msg.id);
        if (_recentMessageIds.length > _maxRecentIds) {
          _recentMessageIds.remove(_recentMessageIds.first);
        }
        return msg;
      }
      if (data != null && resp.statusCode == 403) {
        _isBanned = true;
        _banReason = data['error']?.toString();
        _banStatusController.add(true);
      }
      _errorController.add(data?['error']?.toString() ?? 'Помилка відправки');
    } catch (e) {
      appDebugLog('❌ sendVoiceMessage error: $e');
      _errorController.add('Помилка відправки голосового');
    }
    return null;
  }

  // ── REST: Send image message ──────────────────────────────────────────
  Future<ChatMessage?> sendImageMessage(
    String filePath, {
    String? caption,
  }) async {
    if (_deviceId == null || _nickname == null) return null;
    if (!PurchaseService().isPremium) {
      _errorController.add('Медіа в чаті доступні тільки з PRO');
      return null;
    }

    if (_lastSendTime != null) {
      final diff = DateTime.now().difference(_lastSendTime!).inMilliseconds;
      if (diff < _rateLimitMs) {
        _errorController.add(
          'Зачекайте ${((_rateLimitMs - diff) / 1000).ceil()} сек',
        );
        return null;
      }
    }

    try {
      _lastSendTime = DateTime.now();

      final uri = Uri.parse(ApiConfig.chatUploadImage);
      final request = http.MultipartRequest('POST', uri);
      request.fields['deviceId'] = _deviceId!;
      request.fields['nickname'] = _nickname!;
      request.fields['isPro'] = PurchaseService().isPremium.toString();
      if (_hardwareId != null) request.fields['hardwareId'] = _hardwareId!;
      if (caption != null && caption.isNotEmpty) {
        request.fields['message'] = caption;
      }
      final ext = filePath.toLowerCase().split('.').last;
      final mime = switch (ext) {
        'png' => MediaType('image', 'png'),
        'webp' => MediaType('image', 'webp'),
        'gif' => MediaType('image', 'gif'),
        _ => MediaType('image', 'jpeg'),
      };
      request.files.add(
        await http.MultipartFile.fromPath('image', filePath, contentType: mime),
      );

      await _attachBearerToMultipart(request);
      final streamed = await request.send().timeout(ApiConfig.longHttpTimeout);
      final resp = await http.Response.fromStream(streamed);

      final data = _tryDecodeJson(resp.body);
      if (data != null && resp.statusCode == 200 && data['message'] != null) {
        final msg = ChatMessage.fromJson(
          data['message'] as Map<String, dynamic>,
        );
        _recentMessageIds.add(msg.id);
        if (_recentMessageIds.length > _maxRecentIds) {
          _recentMessageIds.remove(_recentMessageIds.first);
        }
        return msg;
      }
      if (data != null && resp.statusCode == 403) {
        _isBanned = true;
        _banReason = data['error']?.toString();
        _banStatusController.add(true);
      }
      _errorController.add(
        data?['error']?.toString() ?? 'Помилка відправки фото',
      );
    } catch (e) {
      appDebugLog('❌ sendImageMessage error: $e');
      _errorController.add('Помилка відправки фото');
    }
    return null;
  }

  // ── REST: React ────────────────────────────────────────────────────────
  Future<void> react(String messageId, String emoji) async {
    if (_deviceId == null) return;
    try {
      await _ensureToken();
      final headers = await _authHeaders();
      final resp = await http
          .post(
            Uri.parse(ApiConfig.chatReact),
            headers: headers,
            body: json.encode({
              'messageId': messageId,
              'emoji': emoji,
              if (_hardwareId != null) 'hardwareId': _hardwareId,
            }),
          )
          .timeout(ApiConfig.httpTimeout);
      if (resp.statusCode != 200) {
        final data = _tryDecodeJson(resp.body);
        appDebugLog('❌ react error: ${data?['error']}');
      }
    } catch (e) {
      appDebugLog('❌ react error: $e');
    }
  }

  // ── REST: Edit message ─────────────────────────────────────────────────
  Future<ChatMessage?> editMessage(String messageId, String newText) async {
    if (_deviceId == null) return null;
    final trimmed = newText.trim();
    if (trimmed.isEmpty || trimmed.length > maxMessageLength) return null;
    try {
      await _ensureToken();
      final headers = await _authHeaders();
      final req = http.Request(
        'PATCH',
        Uri.parse(ApiConfig.chatMessageById(messageId)),
      );
      req.headers.addAll(headers);
      req.body = json.encode({'message': trimmed});
      final streamed = await req.send().timeout(ApiConfig.httpTimeout);
      final resp = await http.Response.fromStream(streamed);
      final data = _tryDecodeJson(resp.body);
      if (data != null && resp.statusCode == 200 && data['message'] != null) {
        return ChatMessage.fromJson(data['message'] as Map<String, dynamic>);
      }
      if (data != null && resp.statusCode == 400) {
        _errorController.add(
          data['error']?.toString() ?? 'Помилка редагування',
        );
      }
    } catch (e) {
      appDebugLog('❌ editMessage error: $e');
      _errorController.add('Помилка з\'єднання');
    }
    return null;
  }

  // ── REST: Delete message ───────────────────────────────────────────────
  Future<bool> deleteMessage(String messageId) async {
    try {
      await _ensureToken();
      final headers = await _authHeaders();
      final req = http.Request(
        'DELETE',
        Uri.parse(ApiConfig.chatMessageById(messageId)),
      );
      req.headers.addAll(headers);
      final streamed = await req.send().timeout(ApiConfig.httpTimeout);
      return streamed.statusCode == 200;
    } catch (e) {
      appDebugLog('❌ deleteMessage error: $e');
      return false;
    }
  }

  // ── REST: Typing indicator ─────────────────────────────────────────────
  Future<void> sendTyping(bool isTyping) async {
    if (_deviceId == null || _nickname == null) return;
    try {
      await _ensureToken();
      final headers = await _authHeaders();
      await http
          .post(
            Uri.parse(ApiConfig.chatTyping),
            headers: headers,
            body: json.encode({
              'isTyping': isTyping,
              if (_hardwareId != null) 'hardwareId': _hardwareId,
            }),
          )
          .timeout(const Duration(seconds: 5));
    } catch (_) {}
  }

  // ── REST: Check / Register nickname ────────────────────────────────────
  Future<({bool available, String? error})> checkNickname(String nick) async {
    final trimmed = nick.trim();
    if (trimmed.isEmpty) {
      return (available: false, error: 'Введіть нікнейм');
    }
    try {
      final resp = await http
          .post(
            Uri.parse(ApiConfig.chatCheckNickname),
            headers: {'Content-Type': 'application/json'},
            body: json.encode({
              'nickname': trimmed,
              'deviceId': _deviceId,
              if (_hardwareId != null) 'hardwareId': _hardwareId,
            }),
          )
          .timeout(ApiConfig.httpTimeout);
      final data = _tryDecodeJson(resp.body);
      if (data == null) return (available: false, error: 'Помилка перевірки');
      return (
        available: data['available'] == true,
        error: data['error']?.toString(),
      );
    } catch (e) {
      return (available: false, error: 'Помилка перевірки');
    }
  }

  Future<({bool success, String? error})> registerNickname(String nick) async {
    if (_deviceId == null) return (success: false, error: 'Немає device ID');
    final trimmed = nick.trim();
    if (trimmed.isEmpty) {
      return (success: false, error: 'Введіть нікнейм');
    }
    try {
      final body = <String, dynamic>{
        'nickname': trimmed,
        'deviceId': _deviceId,
      };
      if (_hardwareId != null) body['hardwareId'] = _hardwareId!;
      final resp = await http
          .post(
            Uri.parse(ApiConfig.chatRegisterNickname),
            headers: {'Content-Type': 'application/json'},
            body: json.encode(body),
          )
          .timeout(ApiConfig.httpTimeout);
      final data = _tryDecodeJson(resp.body);
      if (data == null) return (success: false, error: 'Помилка реєстрації');
      if (data['success'] == true) {
        _nickname = trimmed;
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('chat_nickname', trimmed);
        // New JWT must include this nickname; old access token still had previous/empty nick.
        await AuthService.login(nickname: trimmed);
        return (success: true, error: null);
      }
      return (success: false, error: data['error']?.toString());
    } catch (e) {
      return (success: false, error: 'Помилка реєстрації');
    }
  }

  // ── REST: Ban check ────────────────────────────────────────────────────
  Future<bool> checkBanStatus() async {
    if (_deviceId == null) return false;
    try {
      final body = <String, dynamic>{'deviceId': _deviceId};
      if (_nickname != null && _nickname!.trim().isNotEmpty) {
        body['nickname'] = _nickname!.trim();
      }
      if (_hardwareId != null) body['hardwareId'] = _hardwareId;
      final resp = await http
          .post(
            Uri.parse(ApiConfig.chatCheckBan),
            headers: {'Content-Type': 'application/json'},
            body: json.encode(body),
          )
          .timeout(ApiConfig.httpTimeout);
      final data = _tryDecodeJson(resp.body);
      if (data == null) return false;
      _isBanned = data['banned'] == true;
      _banReason = data['reason']?.toString();
      _banStatusController.add(_isBanned);
      return _isBanned;
    } catch (_) {
      return false;
    }
  }

  // ── REST: Moderator actions ────────────────────────────────────────────
  Future<({bool success, String? error})> addModerator(String secret) async {
    // Forward to ModeratorService
    final result = await ModeratorService.instance.login(secret);
    if (result == null) {
      _isModerator = true;
      return (success: true, error: null);
    } else {
      _isModerator = false;
      return (success: false, error: result);
    }
  }

  Future<void> removeModerator(String secret) async {
    await ModeratorService.instance.logout();
    _isModerator = false;
  }

  /// Call this to force sync moderator state from ModeratorService (for UI refresh)
  void syncModeratorState() {
    _isModerator = ModeratorService.instance.isModerator;
  }

  /// Ban by nickname only (admin panel quick ban). Uses admin API when secret available.
  Future<bool> banUserByNickname(String nickname, {String? reason}) async {
    final secret = await ModeratorService.instance.getSecret();
    if (secret != null && secret.isNotEmpty) {
      try {
        final resp = await http
            .post(
              Uri.parse(ApiConfig.adminChatBanUser),
              headers: {
                'Content-Type': 'application/json',
                'X-Auth-Secret': secret,
              },
              body: json.encode({
                'nickname': nickname.trim(),
                'reason': reason ?? 'Модератор (адмін панель)',
              }),
            )
            .timeout(ApiConfig.httpTimeout);
        return resp.statusCode == 200;
      } catch (_) {
        return false;
      }
    }
    final result = await banUser(nickname, reason: reason, targetDeviceId: null);
    return result.success;
  }

  Future<({bool success, String? error})> banUser(
    String nickname, {
    String? reason,
    String? targetDeviceId,
  }) async {
    if (_deviceId == null) {
      return (success: false, error: 'Немає device ID');
    }
    try {
      final headers = <String, String>{'Content-Type': 'application/json'};
      final secret = await ModeratorService.instance.getSecret();
      if (secret != null && secret.isNotEmpty) {
        headers['X-Auth-Secret'] = secret;
      }
      final resp = await http
          .post(
            Uri.parse(ApiConfig.chatBanUser),
            headers: headers,
            body: json.encode({
              'nickname': nickname.trim(),
              'deviceId': _deviceId,
              if (targetDeviceId != null && targetDeviceId.isNotEmpty)
                'targetDeviceId': targetDeviceId,
              'reason': reason ?? 'Порушення правил',
            }),
          )
          .timeout(ApiConfig.httpTimeout);
      final data = _tryDecodeJson(resp.body);
      if (resp.statusCode == 200) {
        return (success: true, error: null);
      }
      return (
        success: false,
        error: data?['error']?.toString() ??
            'Помилка блокування (${resp.statusCode})',
      );
    } catch (_) {
      return (success: false, error: 'Помилка з\'єднання');
    }
  }

  /// Unban user. Uses admin API (X-Auth-Secret) when available.
  Future<bool> unbanUser(String nickname) async {
    final secret = await ModeratorService.instance.getSecret();
    if (secret != null && secret.isNotEmpty) {
      try {
        final resp = await http
            .post(
              Uri.parse(ApiConfig.adminChatUnban),
              headers: {
                'Content-Type': 'application/json',
                'X-Auth-Secret': secret,
              },
              body: json.encode({'nickname': nickname}),
            )
            .timeout(ApiConfig.httpTimeout);
        if (resp.statusCode == 200) return true;
      } catch (_) {}
    }
    if (_deviceId == null) return false;
    try {
      final resp = await http
          .post(
            Uri.parse('${ApiConfig.baseUrl}/api/chat/unban'),
            headers: {'Content-Type': 'application/json'},
            body: json.encode({'nickname': nickname, 'deviceId': _deviceId}),
          )
          .timeout(ApiConfig.httpTimeout);
      return resp.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  /// Delete all messages from a user (moderator admin action). Requires X-Auth-Secret.
  Future<int?> deleteAllUserMessages({
    String? nickname,
    String? deviceId,
  }) async {
    final secret = await ModeratorService.instance.getSecret();
    if (secret == null || secret.isEmpty) return null;
    if ((nickname ?? '').trim().isEmpty && (deviceId ?? '').trim().isEmpty) {
      return null;
    }
    try {
      final resp = await http
          .post(
            Uri.parse(ApiConfig.adminChatDeleteUserMessages),
            headers: {
              'Content-Type': 'application/json',
              'X-Auth-Secret': secret,
            },
            body: json.encode({
              if ((nickname ?? '').trim().isNotEmpty)
                'nickname': nickname!.trim(),
              if ((deviceId ?? '').trim().isNotEmpty)
                'deviceId': deviceId!.trim(),
            }),
          )
          .timeout(ApiConfig.httpTimeout);
      if (resp.statusCode == 200) {
        final data = _tryDecodeJson(resp.body);
        return data?['deleted'] as int? ?? 0;
      }
    } catch (_) {}
    return null;
  }

  /// Ban entry with reason and date.
  static BanEntry _banFromJson(Map<String, dynamic> j) {
    return BanEntry(
      nickname: j['nickname']?.toString() ?? '',
      reason: j['reason']?.toString() ?? 'Порушення правил',
      bannedAt: j['banned_at']?.toString(),
      bannedBy: j['banned_by']?.toString(),
    );
  }

  /// Get banned users with details (reason, date). Uses admin API when available.
  Future<List<BanEntry>> getBanListDetails() async {
    final secret = await ModeratorService.instance.getSecret();
    if (secret != null && secret.isNotEmpty) {
      try {
        final resp = await http
            .get(
              Uri.parse(ApiConfig.adminChatBanList),
              headers: {'X-Auth-Secret': secret},
            )
            .timeout(ApiConfig.httpTimeout);
        if (resp.statusCode == 200) {
          final data = _tryDecodeJson(resp.body);
          if (data != null) {
            final details = data['details'] as List?;
            if (details != null) {
              return details
                  .map((e) => _banFromJson(e as Map<String, dynamic>))
                  .toList();
            }
          }
        }
      } catch (_) {}
    }
    if (_deviceId == null) return [];
    try {
      final uri = Uri.parse(
        ApiConfig.chatBanList,
      ).replace(queryParameters: {'deviceId': _deviceId!});
      final resp = await http.get(uri).timeout(ApiConfig.httpTimeout);
      if (resp.statusCode == 200) {
        final data = _tryDecodeJson(resp.body);
        if (data != null) {
          final details = data['details'] as List?;
          if (details != null) {
            return details
                .map((e) => _banFromJson(e as Map<String, dynamic>))
                .toList();
          }
          final banned = (data['banned'] as List?) ?? [];
          return banned
              .map(
                (n) => BanEntry(
                  nickname: n.toString(),
                  reason: '',
                  bannedAt: null,
                  bannedBy: null,
                ),
              )
              .toList();
        }
      }
    } catch (_) {}
    return [];
  }

  /// Get banned users list (nicknames only). For backwards compatibility.
  Future<List<String>> getBanList() async {
    final details = await getBanListDetails();
    return details.map((b) => b.nickname).toList();
  }

  // ── SSE Stream (delegates to DataStreamService singleton) ────────────
  /// Subscribe to chat events from the shared SSE connection.
  /// DataStreamService.connect() must be called separately (typically at app start).
  void connectSSE() {
    if (_sseListening || _disposed) return;
    _sseListening = true;

    final ds = DataStreamService.instance;

    // Online count comes from SSE; avoid an extra full messages fetch here —
    // ChatTab already loads history on open (was doubling work and janking UI).

    _sseSubscriptions.addAll([
      ds.chatOnlineStream.listen((count) {
        _onlineCount = count;
        _onlineController.add(count);
      }),
      ds.chatNewMessageStream.listen((payload) {
        final msg = ChatMessage.fromJson(payload);
        if (_recentMessageIds.contains(msg.id)) return;
        _recentMessageIds.add(msg.id);
        if (_recentMessageIds.length > _maxRecentIds) {
          _recentMessageIds.remove(_recentMessageIds.first);
        }
        _newMessageController.add(msg);
      }),
      ds.chatDeleteStream.listen((payload) {
        final id = payload['messageId']?.toString();
        if (id != null) _deleteController.add(id);
      }),
      ds.chatReactionStream.listen((payload) {
        final msgId = payload['messageId']?.toString();
        final rawReactions = payload['reactions'] as Map<String, dynamic>?;
        if (msgId != null && rawReactions != null) {
          final parsed = <String, List<ReactionInfo>>{};
          rawReactions.forEach((emoji, list) {
            if (list is List) {
              parsed[emoji] = list
                  .map((r) => ReactionInfo.fromJson(r as Map<String, dynamic>))
                  .toList();
            }
          });
          _reactionController.add((messageId: msgId, reactions: parsed));
        }
      }),
      ds.chatEditStream.listen((payload) {
        try {
          final msg = ChatMessage.fromJson(payload);
          _editController.add(msg);
        } catch (_) {}
      }),
      ds.chatTypingStream.listen((payload) {
        final users = ((payload['users'] as List?) ?? []).cast<String>();
        _typingController.add(users);
      }),
    ]);

    appDebugLog('💬 ChatService: subscribed to DataStreamService');
  }

  void disconnectSSE() {
    _sseListening = false;
    for (final sub in _sseSubscriptions) {
      sub.cancel();
    }
    _sseSubscriptions.clear();
  }

  // ── Report & Block (client-side) ──────────────────────────────────────

  final Set<String> _blockedUserIds = {};

  Future<bool> reportMessage(
    String messageId,
    String reason, {
    String? reportedDeviceId,
    String? reportedNickname,
    String? originalText,
  }) async {
    try {
      final resp = await AuthService.authenticatedRequest(
        'POST',
        '/api/chat/report',
        body: {
          'messageId': messageId,
          'originalText': originalText ?? '',
          'reportedDeviceId': reportedDeviceId,
          'reportedNickname': reportedNickname,
          'reason': reason,
        },
      );
      return resp.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  void blockUser(String userId) {
    final key = userId.trim().toLowerCase();
    if (key.isEmpty) return;
    _blockedUserIds.add(key);
    _saveBlockList();
  }

  void unblockUser(String userId) {
    _blockedUserIds.remove(userId.trim().toLowerCase());
    _saveBlockList();
  }

  Set<String> get blockedUserIds => Set.unmodifiable(_blockedUserIds);

  bool isBlocked(String userId) {
    final key = userId.trim().toLowerCase();
    if (key.isEmpty) return false;
    return _blockedUserIds.contains(key);
  }

  Future<void> _saveBlockList() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setStringList('chat_block_list', _blockedUserIds.toList());
    } catch (_) {}
  }

  Future<void> loadBlockList() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final list = prefs.getStringList('chat_block_list') ?? [];
      _blockedUserIds.clear();
      for (final id in list) {
        final key = id.trim().toLowerCase();
        if (key.isNotEmpty) _blockedUserIds.add(key);
      }
    } catch (_) {}
  }

  // ── Cleanup ────────────────────────────────────────────────────────────
  Future<String> getTemporaryDirectoryPath() async {
    final dir = await getTemporaryDirectory();
    return dir.path;
  }

  void dispose() {
    _disposed = true;
    disconnectSSE();
    _messagesController.close();
    _newMessageController.close();
    _deleteController.close();
    _reactionController.close();
    _typingController.close();
    _onlineController.close();
    _banStatusController.close();
    _errorController.close();
  }
}
