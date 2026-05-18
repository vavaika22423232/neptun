import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:record/record.dart';
import 'package:audioplayers/audioplayers.dart';

import 'package:neptun_alarm_app/models/chat_message.dart';
import 'package:neptun_alarm_app/services/chat_service.dart';
import 'package:neptun_alarm_app/services/purchase_service.dart';
import 'package:neptun_alarm_app/config/api_config.dart';
import 'package:neptun_alarm_app/config/prefs_keys.dart';
import 'package:neptun_alarm_app/core/utils/connectivity_utils.dart';
import 'package:neptun_alarm_app/core/pro/pro_features.dart';
import 'package:neptun_alarm_app/core/utils/app_debug_log.dart';
import 'package:neptun_alarm_app/core/providers/providers.dart';
import 'package:image_picker/image_picker.dart';
import 'package:flutter_image_compress/flutter_image_compress.dart';
import 'package:path_provider/path_provider.dart';
import 'chat_state.dart';

class ChatNotifier extends Notifier<ChatState> {
  final AudioRecorder _recorder = AudioRecorder();
  final AudioPlayer _audioPlayer = AudioPlayer();
  final ImagePicker _imagePicker = ImagePicker();

  final List<StreamSubscription<dynamic>> _subscriptions = [];
  Timer? _typingTimer;
  Timer? _recordingTimer;

  @override
  ChatState build() {
    final chatService = ref.watch(chatServiceProvider);

    Future.microtask(() => _init(chatService));

    ref.onDispose(() {
      for (final sub in _subscriptions) {
        sub.cancel();
      }
      _typingTimer?.cancel();
      _recordingTimer?.cancel();
      _recorder.dispose();
      _audioPlayer.dispose();
    });

    return const ChatState();
  }

  Future<void> _init(ChatService chatService) async {
    try {
      if (chatService.deviceId == null) {
        await chatService.init();
      }
      await chatService.loadBlockList();

      final messages = await chatService.fetchMessages();
      final filtered = messages
          .where((m) => !chatService.isBlocked(m.userId))
          .toList();

      chatService.connectSSE();
      await chatService.restorePendingFromQueue();
      final queue = await chatService.getOfflineQueue();
      final synthetics = _buildSynthetics(queue, filtered, chatService);

      final prefs = ref.read(sharedPreferencesProvider);
      final ageConfirmed = prefs.getBool(PrefsKeys.chatAgeConfirmed) ?? false;
      final rulesAgreed = prefs.getBool(PrefsKeys.chatRulesAgreed) ?? false;
      final needsRegistration = chatService.nickname == null;

      state = state.copyWith(
        messages: [...synthetics, ...filtered],
        isLoading: false,
        ageConfirmed: ageConfirmed,
        rulesAgreed: rulesAgreed,
        needsRegistration: needsRegistration,
        isBanned: chatService.isBanned,
        banReason: chatService.banReason,
        onlineCount: chatService.onlineCount,
      );

      _setupSubscriptions(chatService);

      if (await isConnectivityOnline()) {
        await chatService.flushOfflineQueue();
      }
    } catch (e, st) {
      appDebugLog('Chat', '_init failed: $e\n$st');
      state = state.copyWith(isLoading: false);
    }
  }

  List<ChatMessage> _buildSynthetics(
    List<Map<String, dynamic>> queue,
    List<ChatMessage> filtered,
    ChatService chatService,
  ) {
    final synthetics = <ChatMessage>[];
    for (var i = queue.length - 1; i >= 0; i--) {
      final item = queue[i];
      final pendingId = item['pendingId']?.toString() ?? '';
      final text = item['text']?.toString() ?? '';
      final replyToId = item['replyToId']?.toString();
      if (pendingId.isEmpty || text.isEmpty) continue;

      ChatMessage? replyTo;
      if (replyToId != null && replyToId.isNotEmpty) {
        final found = filtered.where((m) => m.id == replyToId).toList();
        replyTo = found.isNotEmpty ? found.first : null;
      }

      synthetics.add(
        ChatMessage(
          id: pendingId,
          userId: chatService.nickname ?? 'Ви',
          deviceId: chatService.deviceId ?? '',
          message: text,
          timestamp: DateTime.now().millisecondsSinceEpoch,
          replyTo: replyTo != null
              ? ReplyInfo(
                  id: replyTo.id,
                  nickname: replyTo.userId,
                  text: replyTo.message,
                )
              : null,
          isPro: PurchaseService().isPremium,
        ),
      );
    }
    return synthetics;
  }

  void _setupSubscriptions(ChatService chatService) {
    _subscriptions.add(chatService.newMessageStream.listen(_onNewMessage));
    _subscriptions.add(chatService.deleteStream.listen(_onDeleteMessage));
    _subscriptions.add(chatService.reactionStream.listen(_onReaction));
    _subscriptions.add(chatService.editStream.listen(_onEditMessage));
    _subscriptions.add(
      chatService.typingStream.listen((users) {
        final me = (chatService.nickname ?? '').trim().toLowerCase();
        state = state.copyWith(
          typingUsers: users
              .where((u) {
                final n = u.trim().toLowerCase();
                return n.isNotEmpty && n != me;
              })
              .where((u) => !chatService.isBlocked(u))
              .toList(),
        );
      }),
    );
    _subscriptions.add(
      chatService.blockListStream.listen((_) {
        final s = ref.read(chatServiceProvider);
        state = state.copyWith(
          messages: state.messages
              .where((m) => !s.isBlocked(m.userId))
              .toList(),
        );
      }),
    );
    _subscriptions.add(
      chatService.onlineStream.listen((count) {
        state = state.copyWith(onlineCount: count);
      }),
    );
    _subscriptions.add(
      chatService.banStatusStream.listen((banned) {
        state = state.copyWith(
          isBanned: banned,
          banReason: chatService.banReason,
        );
      }),
    );
    _subscriptions.add(
      chatService.pendingResolvedStream.listen((event) {
        if (ref.read(chatServiceProvider).isBlocked(event.message.userId)) {
          return;
        }
        final messages = List<ChatMessage>.from(state.messages);
        final idx = messages.indexWhere((m) => m.id == event.pendingId);
        if (idx != -1) {
          messages[idx] = event.message;
        } else if (!messages.any((m) => m.id == event.message.id)) {
          messages.insert(0, event.message);
        }
        state = state.copyWith(messages: messages);
      }),
    );

    _subscriptions.add(
      _audioPlayer.onPlayerComplete.listen((_) {
        state = state.copyWith(isPlaying: false, playingMessageId: null);
      }),
    );
  }

  void _onNewMessage(ChatMessage msg) {
    if (state.messages.any((m) => m.id == msg.id)) return;
    final chatService = ref.read(chatServiceProvider);
    if (chatService.isBlocked(msg.userId)) return;

    final messages = [msg, ...state.messages];
    if (messages.length > 200) messages.removeLast();
    state = state.copyWith(messages: messages);
  }

  void _onDeleteMessage(String id) {
    state = state.copyWith(
      messages: state.messages.where((m) => m.id != id).toList(),
    );
  }

  void _onReaction(
    ({String messageId, Map<String, List<ReactionInfo>> reactions}) event,
  ) {
    final messages = state.messages.map((m) {
      if (m.id == event.messageId) {
        return m.copyWithReactions(event.reactions);
      }
      return m;
    }).toList();
    state = state.copyWith(messages: messages);
  }

  void _onEditMessage(ChatMessage edited) {
    final chatService = ref.read(chatServiceProvider);
    if (chatService.isBlocked(edited.userId)) {
      state = state.copyWith(
        messages: state.messages.where((m) => m.id != edited.id).toList(),
        clearEdit: state.editingMessage?.id == edited.id,
      );
      return;
    }
    final messages = state.messages.map((m) {
      if (m.id == edited.id) return edited;
      return m;
    }).toList();

    final clearEdit = state.editingMessage?.id == edited.id;
    state = state.copyWith(messages: messages, clearEdit: clearEdit);
  }

  Future<void> loadMoreMessages() async {
    if (state.isLoadingMore ||
        !state.hasMoreHistory ||
        state.messages.isEmpty) {
      return;
    }

    final chatService = ref.read(chatServiceProvider);
    final oldest = state.messages.last;
    final beforeSec = oldest.timestamp < 10000000000
        ? oldest.timestamp
        : (oldest.timestamp / 1000).round();

    state = state.copyWith(isLoadingMore: true);
    final older = await chatService.fetchMoreMessages(beforeSec);

    final filtered = older
        .where((m) => !chatService.isBlocked(m.userId))
        .where((m) => !state.messages.any((x) => x.id == m.id))
        .toList();

    state = state.copyWith(
      messages: [...state.messages, ...filtered],
      isLoadingMore: false,
      hasMoreHistory: filtered.length >= 50,
    );
  }

  Future<void> sendMessage(String text) async {
    final trimmed = text.trim();
    if (trimmed.isEmpty) return;

    final chatService = ref.read(chatServiceProvider);
    final editingMessage = state.editingMessage;
    if (editingMessage != null) {
      state = state.copyWith(clearEdit: true, isSending: true);
      final updated = await chatService.editMessage(editingMessage.id, trimmed);
      state = state.copyWith(isSending: false);
      if (updated != null) _onEditMessage(updated);
      return;
    }

    final replyTo = state.replyTo;
    state = state.copyWith(clearReply: true);

    final pendingId = 'pending-${DateTime.now().millisecondsSinceEpoch}';
    final optimistic = ChatMessage(
      id: pendingId,
      userId: chatService.nickname ?? 'Ви',
      deviceId: chatService.deviceId ?? '',
      message: trimmed,
      timestamp: DateTime.now().millisecondsSinceEpoch,
      replyTo: replyTo != null
          ? ReplyInfo(
              id: replyTo.id,
              nickname: replyTo.userId,
              text: replyTo.message,
            )
          : null,
      isPro: PurchaseService().isPremium,
    );

    state = state.copyWith(messages: [optimistic, ...state.messages]);

    final sent = await chatService.sendMessage(trimmed, replyToId: replyTo?.id);
    if (sent != null) {
      state = state.copyWith(
        messages: state.messages.where((m) => m.id != pendingId).toList(),
      );
      _onNewMessage(sent);
    } else {
      await chatService.addToOfflineQueue(
        pendingId: pendingId,
        text: trimmed,
        replyToId: replyTo?.id,
      );
    }
  }

  void setReply(ChatMessage? msg) =>
      state = state.copyWith(replyTo: msg, clearReply: msg == null);
  void setEdit(ChatMessage? msg) =>
      state = state.copyWith(editingMessage: msg, clearEdit: msg == null);

  Future<void> startRecording() async {
    if (!ProGate.isUnlocked(ProFeature.chatMedia)) return;
    try {
      if (!await _recorder.hasPermission()) return;

      final chatService = ref.read(chatServiceProvider);
      final dir = await chatService.getTemporaryDirectoryPath();
      final path = '$dir/voice_${DateTime.now().millisecondsSinceEpoch}.m4a';

      await _recorder.start(
        const RecordConfig(encoder: AudioEncoder.aacLc, bitRate: 128000),
        path: path,
      );

      state = state.copyWith(isRecording: true, recordingSeconds: 0);
      _recordingTimer = Timer.periodic(const Duration(seconds: 1), (_) {
        state = state.copyWith(recordingSeconds: state.recordingSeconds + 1);
        if (state.recordingSeconds >= 60) stopAndSendRecording();
      });
    } catch (e) {
      appDebugLog('Chat', 'Recording start error: $e');
    }
  }

  Future<void> cancelRecording() async {
    _recordingTimer?.cancel();
    await _recorder.stop();
    state = state.copyWith(isRecording: false, recordingSeconds: 0);
  }

  Future<void> stopAndSendRecording() async {
    _recordingTimer?.cancel();
    if (!state.isRecording) return;

    final duration = state.recordingSeconds;
    state = state.copyWith(isRecording: false, recordingSeconds: 0);
    if (duration < 1) return;

    if (!ProGate.isUnlocked(ProFeature.chatMedia)) {
      try {
        await _recorder.stop();
      } catch (_) {}
      return;
    }

    try {
      final chatService = ref.read(chatServiceProvider);
      final path = await _recorder.stop();
      if (path == null) return;

      state = state.copyWith(isSending: true);
      final sent = await chatService.sendVoiceMessage(path, duration);
      state = state.copyWith(isSending: false);
      if (sent != null) _onNewMessage(sent);
    } catch (e) {
      appDebugLog('Chat', 'Voice send error: $e');
    }
  }

  Future<void> togglePlayback(String messageId, String url) async {
    final fullUrl = ApiConfig.absoluteUrl(url);
    if (fullUrl.isEmpty) {
      appDebugLog('Chat', 'togglePlayback — empty audio URL');
      return;
    }

    if (state.playingMessageId == messageId && state.isPlaying) {
      await _audioPlayer.pause();
      state = state.copyWith(isPlaying: false);
      return;
    }

    try {
      if (state.playingMessageId != messageId) {
        await _audioPlayer.stop();
        await _audioPlayer.play(UrlSource(fullUrl));
      } else {
        await _audioPlayer.resume();
      }
      state = state.copyWith(playingMessageId: messageId, isPlaying: true);
    } catch (e) {
      appDebugLog('Chat', 'voice playback error: $e (url=$fullUrl)');
      state = state.copyWith(isPlaying: false, playingMessageId: null);
    }
  }

  void confirmAge(int birthYear) async {
    final currentYear = DateTime.now().year;
    if (currentYear - birthYear < 16) return;

    final prefs = ref.read(sharedPreferencesProvider);
    await prefs.setBool(PrefsKeys.chatAgeConfirmed, true);
    state = state.copyWith(ageConfirmed: true);
  }

  void agreeToRules() async {
    final prefs = ref.read(sharedPreferencesProvider);
    await prefs.setBool(PrefsKeys.chatRulesAgreed, true);
    state = state.copyWith(rulesAgreed: true);
  }

  Future<void> registerNickname(String nick) async {
    final chatService = ref.read(chatServiceProvider);
    final result = await chatService.registerNickname(nick);
    if (result.success) {
      final messages = await chatService.fetchMessages();
      state = state.copyWith(needsRegistration: false, messages: messages);
    }
  }

  void setSearchMode(bool active) {
    state = state.copyWith(
      searchMode: active,
      searchQuery: active ? state.searchQuery : '',
      searchResults: active ? state.searchResults : const [],
    );
  }

  void updateSearch(String query) {
    final q = query.trim().toLowerCase();
    if (q.isEmpty) {
      state = state.copyWith(
        searchQuery: '',
        searchResults: const [],
        searchCurrentIndex: 0,
      );
      return;
    }

    final results = <int>[];
    for (var i = 0; i < state.messages.length; i++) {
      if (state.messages[i].message.toLowerCase().contains(q)) results.add(i);
    }
    state = state.copyWith(
      searchQuery: q,
      searchResults: results,
      searchCurrentIndex: results.isNotEmpty ? 0 : -1,
    );
  }

  void nextSearchResult(int delta) {
    if (state.searchResults.isEmpty) return;
    var idx = state.searchCurrentIndex + delta;
    if (idx < 0) idx = state.searchResults.length - 1;
    if (idx >= state.searchResults.length) idx = 0;
    state = state.copyWith(searchCurrentIndex: idx);
  }

  Future<void> pickAndSendImage(ImageSource source, {String? caption}) async {
    if (!ProGate.isUnlocked(ProFeature.chatMedia)) return;
    try {
      final xFile = await _imagePicker.pickImage(
        source: source,
        maxWidth: 1920,
        imageQuality: 85,
      );
      if (xFile == null) return;

      final dir = await getTemporaryDirectory();
      final targetPath =
          '${dir.path}/chat_img_${DateTime.now().millisecondsSinceEpoch}.jpg';

      final compressed = await FlutterImageCompress.compressAndGetFile(
        xFile.path,
        targetPath,
        minWidth: 1920,
        minHeight: 1920,
        quality: 85,
        format: CompressFormat.jpeg,
      );

      final chatService = ref.read(chatServiceProvider);
      state = state.copyWith(isSending: true);

      final sent = await chatService.sendImageMessage(
        compressed?.path ?? xFile.path,
        caption: caption?.trim().isEmpty == true ? null : caption,
      );

      state = state.copyWith(isSending: false);
      if (sent != null) _onNewMessage(sent);
    } catch (e) {
      appDebugLog('Chat', 'Image picking/send error: $e');
      state = state.copyWith(isSending: false);
    }
  }
}

final chatControllerProvider = NotifierProvider<ChatNotifier, ChatState>(
  ChatNotifier.new,
);
