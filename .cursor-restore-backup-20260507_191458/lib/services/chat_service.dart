import 'dart:async';
import 'dart:convert';
import 'dart:io' show Platform;
import 'package:android_id/android_id.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';
import 'package:path_provider/path_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../config/api_config.dart';
import '../config/prefs_keys.dart';
import '../models/chat_message.dart';
import 'auth_service.dart';
import 'chat/ban_entry.dart';
import 'chat/chat_json_utils.dart';
import 'moderator_service.dart';
import 'purchase_service.dart';
import 'data_stream_service.dart';

export 'chat/ban_entry.dart' show BanEntry;

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

  /// Flush offline queue: send each message, on success emit (pendingId, realMessage).
  Future<void> flushOfflineQueue() async {
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

  // ── Rate limiter ───────────────────────────────────────────────────────
  DateTime? _lastSendTime;
  static const _rateLimitMs = 3000;
  static const _maxMessageLength = 500;

  // ── Initialization ─────────────────────────────────────────────────────
  Future<void> init() async {
    final prefs = await SharedPreferences.getInstance();
    _deviceId = await AuthService.getDeviceId();
    _nickname = prefs.getString('chat_nickname');
    if (Platform.isAndroid) {
      try {
        final id = await const AndroidId().getId();
        if (id != null && id.isNotEmpty) _hardwareId = id;
      } catch (_) {}
    }
    if (await AuthService.getAccessToken() == null) {
      await AuthService.login(nickname: _nickname);
    }
    // Sync moderator state from ModeratorService
    _isModerator = ModeratorService.instance.isModerator;
    // Listen for moderator state changes
    ModeratorService.instance.stream.listen((isMod) {
      _isModerator = isMod;
    });
    // Load block list so isBlocked works before chat opens
    await loadBlockList();
    // Check ban in background
    unawaited(checkBanStatus());
    // Flush offline queue when connectivity restored (works even when chat tab not open)
    Connectivity().onConnectivityChanged.listen((results) async {
      final hasConnection = results.any(
        (r) =>
            r == ConnectivityResult.mobile ||
            r == ConnectivityResult.wifi ||
            r == ConnectivityResult.ethernet,
      );
      if (hasConnection) await flushOfflineQueue();
    });
  }

  // ── REST: Fetch messages ───────────────────────────────────────────────
  /// Fetches messages. Use [before] (timestamp in seconds) for pagination.
  Future<List<ChatMessage>> fetchMessages({int? before, int limit = 50}) async {
    try {
      var url = ApiConfig.chatMessages;
      if (before != null) {
        url = '$url?before=$before&limit=$limit';
      } else {
        url = '$url?limit=200';
      }
      final resp = await http
          .get(Uri.parse(url), headers: await AuthService.getAuthHeaders())
          .timeout(ApiConfig.httpTimeout);
      if (resp.statusCode == 200) {
        final data = tryDecodeJsonObject(resp.body);
        if (data == null) {
          debugPrint('❌ fetchMessages: invalid response (HTML?)');
          return [];
        }
        final raw = (data['messages'] as List?) ?? [];
        // Fallback: use fetch's "recently active" count until SSE delivers real-time count.
        // SSE 'connected' and 'online' events will overwrite with correct value.
        final fetchOnline = parseChatOnlineCount(data['online']);
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
      debugPrint('❌ fetchMessages error: $e');
      _errorController.add('Помилка завантаження повідомлень');
    }
    return [];
  }

  /// Fetches older messages for pagination. Returns messages older than [beforeTimestamp].
  Future<List<ChatMessage>> fetchMoreMessages(int beforeTimestamp) async {
    return fetchMessages(before: beforeTimestamp, limit: 50);
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
    if (trimmed.length > _maxMessageLength) {
      _errorController.add(
        'Повідомлення занадто довге (макс $_maxMessageLength)',
      );
      return null;
    }

    try {
      _lastSendTime = DateTime.now();
      final body = <String, dynamic>{
        'deviceId': _deviceId,
        'nickname': _nickname,
        'message': trimmed,
        'isPro': PurchaseService().isPremium,
      };
      if (replyToId != null) body['replyTo'] = replyToId;
      if (_hardwareId != null) body['hardwareId'] = _hardwareId;

      final resp = await http
          .post(
            Uri.parse(ApiConfig.chatSend),
            headers: await AuthService.getAuthHeaders(),
            body: json.encode(body),
          )
          .timeout(ApiConfig.httpTimeout);

      final data = tryDecodeJsonObject(resp.body);
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
      debugPrint('❌ sendMessage error: $e');
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
      request.headers.addAll(await AuthService.getAuthHeaders());
      request.headers.remove('Content-Type');
      request.fields['deviceId'] = _deviceId!;
      request.fields['nickname'] = _nickname!;
      request.fields['duration'] = durationSeconds.toString();
      request.fields['isPro'] = PurchaseService().isPremium.toString();
      if (_hardwareId != null) request.fields['hardwareId'] = _hardwareId!;
      request.files.add(await http.MultipartFile.fromPath('audio', filePath));

      final streamed = await request.send().timeout(ApiConfig.longHttpTimeout);
      final resp = await http.Response.fromStream(streamed);

      final data = tryDecodeJsonObject(resp.body);
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
      debugPrint('❌ sendVoiceMessage error: $e');
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
      request.headers.addAll(await AuthService.getAuthHeaders());
      request.headers.remove('Content-Type');
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

      final streamed = await request.send().timeout(ApiConfig.longHttpTimeout);
      final resp = await http.Response.fromStream(streamed);

      final data = tryDecodeJsonObject(resp.body);
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
      debugPrint('❌ sendImageMessage error: $e');
      _errorController.add('Помилка відправки фото');
    }
    return null;
  }

  // ── REST: React ────────────────────────────────────────────────────────
  Future<void> react(String messageId, String emoji) async {
    if (_deviceId == null) return;
    try {
      final resp = await http
          .post(
            Uri.parse(ApiConfig.chatReact),
            headers: await AuthService.getAuthHeaders(),
            body: json.encode({
              'messageId': messageId,
              'emoji': emoji,
              'deviceId': _deviceId,
              'nickname': _nickname ?? '',
              if (_hardwareId != null) 'hardwareId': _hardwareId,
            }),
          )
          .timeout(ApiConfig.httpTimeout);
      if (resp.statusCode != 200) {
        final data = tryDecodeJsonObject(resp.body);
        debugPrint('❌ react error: ${data?['error']}');
      }
    } catch (e) {
      debugPrint('❌ react error: $e');
    }
  }

  // ── REST: Edit message ─────────────────────────────────────────────────
  Future<ChatMessage?> editMessage(String messageId, String newText) async {
    if (_deviceId == null) return null;
    final trimmed = newText.trim();
    if (trimmed.isEmpty || trimmed.length > _maxMessageLength) return null;
    try {
      final req = http.Request(
        'PATCH',
        Uri.parse(ApiConfig.chatMessageById(messageId)),
      );
      req.headers.addAll(await AuthService.getAuthHeaders());
      req.body = json.encode({'deviceId': _deviceId, 'message': trimmed});
      final streamed = await req.send().timeout(ApiConfig.httpTimeout);
      final resp = await http.Response.fromStream(streamed);
      final data = tryDecodeJsonObject(resp.body);
      if (data != null && resp.statusCode == 200 && data['message'] != null) {
        return ChatMessage.fromJson(data['message'] as Map<String, dynamic>);
      }
      if (data != null && resp.statusCode == 400) {
        _errorController.add(
          data['error']?.toString() ?? 'Помилка редагування',
        );
      }
    } catch (e) {
      debugPrint('❌ editMessage error: $e');
      _errorController.add('Помилка з\'єднання');
    }
    return null;
  }

  // ── REST: Delete message ───────────────────────────────────────────────
  Future<bool> deleteMessage(String messageId) async {
    try {
      final req = http.Request(
        'DELETE',
        Uri.parse(ApiConfig.chatMessageById(messageId)),
      );
      req.headers.addAll(await AuthService.getAuthHeaders());
      req.body = json.encode({'deviceId': _deviceId});
      final streamed = await req.send().timeout(ApiConfig.httpTimeout);
      return streamed.statusCode == 200;
    } catch (e) {
      debugPrint('❌ deleteMessage error: $e');
      return false;
    }
  }

  // ── REST: Typing indicator ─────────────────────────────────────────────
  Future<void> sendTyping(bool isTyping) async {
    if (_deviceId == null || _nickname == null) return;
    try {
      await http
          .post(
            Uri.parse(ApiConfig.chatTyping),
            headers: await AuthService.getAuthHeaders(),
            body: json.encode({
              'deviceId': _deviceId,
              'nickname': _nickname,
              'isTyping': isTyping,
              if (_hardwareId != null) 'hardwareId': _hardwareId,
            }),
          )
          .timeout(const Duration(seconds: 5));
    } catch (_) {}
  }

  // ── REST: Check / Register nickname ────────────────────────────────────
  Future<({bool available, String? error})> checkNickname(String nick) async {
    try {
      final resp = await http
          .post(
            Uri.parse(ApiConfig.chatCheckNickname),
            headers: {'Content-Type': 'application/json'},
            body: json.encode({
              'nickname': nick,
              'deviceId': _deviceId,
              if (_hardwareId != null) 'hardwareId': _hardwareId,
            }),
          )
          .timeout(ApiConfig.httpTimeout);
      final data = tryDecodeJsonObject(resp.body);
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
    try {
      final body = <String, dynamic>{'nickname': nick, 'deviceId': _deviceId};
      if (_hardwareId != null) body['hardwareId'] = _hardwareId!;
      final resp = await http
          .post(
            Uri.parse(ApiConfig.chatRegisterNickname),
            headers: {'Content-Type': 'application/json'},
            body: json.encode(body),
          )
          .timeout(ApiConfig.httpTimeout);
      final data = tryDecodeJsonObject(resp.body);
      if (data == null) return (success: false, error: 'Помилка реєстрації');
      if (data['success'] == true) {
        _nickname = nick;
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('chat_nickname', nick);
        await AuthService.login(nickname: nick);
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
      if (_hardwareId != null) body['hardwareId'] = _hardwareId;
      final nick = (_nickname ?? '').trim();
      if (nick.isNotEmpty) body['nickname'] = nick;
      final resp = await http
          .post(
            Uri.parse(ApiConfig.chatCheckBan),
            headers: {'Content-Type': 'application/json'},
            body: json.encode(body),
          )
          .timeout(ApiConfig.httpTimeout);
      final data = tryDecodeJsonObject(resp.body);
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
    return banUser(nickname, reason: reason, targetDeviceId: null);
  }

  Future<bool> banUser(
    String nickname, {
    String? reason,
    String? targetDeviceId,
  }) async {
    final nick = nickname.trim();
    final targetDev = targetDeviceId?.trim() ?? '';
    final secret = await ModeratorService.instance.getSecret();

    // Admin API: secret is the same as moderator login; send nick and/or offender device.
    if (secret != null && secret.isNotEmpty) {
      if (nick.isEmpty && targetDev.isEmpty) return false;
      try {
        final body = <String, dynamic>{'reason': reason ?? 'Порушення правил'};
        if (nick.isNotEmpty) body['nickname'] = nick;
        if (targetDev.isNotEmpty) body['deviceId'] = targetDev;
        final resp = await http
            .post(
              Uri.parse(ApiConfig.adminChatBanUser),
              headers: {
                'Content-Type': 'application/json',
                'X-Auth-Secret': secret,
              },
              body: json.encode(body),
            )
            .timeout(ApiConfig.httpTimeout);
        if (resp.statusCode == 200) return true;
      } catch (_) {}
    }

    // Fallback: moderator device in body; targetDeviceId = offender (server used to ignore it — empty device_id bans).
    if (_deviceId == null) return false;
    if (nick.isEmpty && targetDev.isEmpty) return false;
    try {
      final body = <String, dynamic>{
        'deviceId': _deviceId,
        'reason': reason ?? 'Порушення правил',
      };
      if (nick.isNotEmpty) body['nickname'] = nick;
      if (targetDev.isNotEmpty) body['targetDeviceId'] = targetDev;
      final resp = await http
          .post(
            Uri.parse(ApiConfig.chatBanUser),
            headers: {'Content-Type': 'application/json'},
            body: json.encode(body),
          )
          .timeout(ApiConfig.httpTimeout);
      return resp.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  /// Unban user. Uses admin API (X-Auth-Secret) when available.
  Future<bool> unbanUser(
    String nickname, {
    String? targetDeviceId,
    String? hardwareId,
  }) async {
    final secret = await ModeratorService.instance.getSecret();
    if (secret != null && secret.isNotEmpty) {
      try {
        final body = <String, dynamic>{
          if (nickname.trim().isNotEmpty) 'nickname': nickname.trim(),
          if ((targetDeviceId ?? '').trim().isNotEmpty)
            'deviceId': targetDeviceId!.trim(),
          if ((hardwareId ?? '').trim().isNotEmpty)
            'hardwareId': hardwareId!.trim(),
        };
        final resp = await http
            .post(
              Uri.parse(ApiConfig.adminChatUnban),
              headers: {
                'Content-Type': 'application/json',
                'X-Auth-Secret': secret,
              },
              body: json.encode(body),
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
            body: json.encode({
              if (nickname.trim().isNotEmpty) 'nickname': nickname.trim(),
              'deviceId': _deviceId,
              if ((targetDeviceId ?? '').trim().isNotEmpty)
                'targetDeviceId': targetDeviceId!.trim(),
              if ((hardwareId ?? '').trim().isNotEmpty)
                'hardwareId': hardwareId!.trim(),
            }),
          )
          .timeout(ApiConfig.httpTimeout);
      return resp.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  Future<bool> unbanEntry(BanEntry ban) {
    return unbanUser(
      ban.nickname,
      targetDeviceId: ban.deviceId,
      hardwareId: ban.hardwareId,
    );
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
      final resp = await http.post(
        Uri.parse(ApiConfig.adminChatDeleteUserMessages),
        headers: {'Content-Type': 'application/json', 'X-Auth-Secret': secret},
        body: json.encode({
          if ((nickname ?? '').trim().isNotEmpty) 'nickname': nickname!.trim(),
          if ((deviceId ?? '').trim().isNotEmpty) 'deviceId': deviceId!.trim(),
        }),
      );
      if (resp.statusCode == 200) {
        final data = tryDecodeJsonObject(resp.body);
        return data?['deleted'] as int? ?? 0;
      }
    } catch (_) {}
    return null;
  }

  /// Get banned users with details (reason, date). Uses admin API when available.
  Future<List<BanEntry>> getBanListDetails({String query = ''}) async {
    final q = query.trim();
    final secret = await ModeratorService.instance.getSecret();
    if (secret != null && secret.isNotEmpty) {
      try {
        final uri = q.isEmpty
            ? Uri.parse(ApiConfig.adminChatBanList)
            : Uri.parse(
                ApiConfig.adminChatBanList,
              ).replace(queryParameters: {'q': q});
        final resp = await http
            .get(uri, headers: {'X-Auth-Secret': secret})
            .timeout(ApiConfig.httpTimeout);
        if (resp.statusCode == 200) {
          final data = tryDecodeJsonObject(resp.body);
          if (data != null) {
            final details = data['details'] as List?;
            if (details != null) {
              return details
                  .map((e) => banEntryFromJson(e as Map<String, dynamic>))
                  .toList();
            }
          }
        }
      } catch (_) {}
    }
    if (_deviceId == null) return [];
    try {
      final uri = Uri.parse(ApiConfig.chatBanList).replace(
        queryParameters: {'deviceId': _deviceId!, if (q.isNotEmpty) 'q': q},
      );
      final resp = await http.get(uri).timeout(ApiConfig.httpTimeout);
      if (resp.statusCode == 200) {
        final data = tryDecodeJsonObject(resp.body);
        if (data != null) {
          final details = data['details'] as List?;
          if (details != null) {
            return details
                .map((e) => banEntryFromJson(e as Map<String, dynamic>))
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

    // Pre-fetch messages to get initial online count (fallback until SSE delivers)
    unawaited(fetchMessages());

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

    debugPrint('💬 ChatService: subscribed to DataStreamService');
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
  final StreamController<List<String>> _blockListController =
      StreamController<List<String>>.broadcast();

  /// Поточний список заблокованих (device id / ключ), оновлюється при зміні блок-листа.
  Stream<List<String>> get blockListStream => _blockListController.stream;

  void _notifyBlockList() {
    if (!_blockListController.isClosed) {
      _blockListController.add(_blockedUserIds.toList());
    }
  }

  /// Тимчасова тека кешу (зображення/аудіо чату).
  Future<String> getTemporaryDirectoryPath() async {
    final d = await getTemporaryDirectory();
    return d.path;
  }

  Future<bool> reportMessage(
    String messageId,
    String reason, {
    String? reportedDeviceId,
    String? reportedNickname,
    String? originalText,
  }) async {
    try {
      final resp = await http
          .post(
            Uri.parse('${ApiConfig.baseUrl}/api/chat/report'),
            headers: {'Content-Type': 'application/json'},
            body: json.encode({
              'messageId': messageId,
              'reporterDeviceId': _deviceId,
              'reporterNickname': _nickname ?? 'Анонім',
              'originalText': originalText ?? '',
              'reportedDeviceId': reportedDeviceId,
              'reportedNickname': reportedNickname,
              'reason': reason,
            }),
          )
          .timeout(ApiConfig.httpTimeout);
      return resp.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  void blockUser(String userId) {
    final key = userId.trim().toLowerCase();
    if (key.isEmpty) return;
    _blockedUserIds.add(key);
    _notifyBlockList();
    _saveBlockList();
  }

  void unblockUser(String userId) {
    _blockedUserIds.remove(userId.trim().toLowerCase());
    _notifyBlockList();
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
      _notifyBlockList();
    } catch (_) {}
  }

  // ── Cleanup ────────────────────────────────────────────────────────────
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
    if (!_blockListController.isClosed) {
      _blockListController.close();
    }
  }
}
