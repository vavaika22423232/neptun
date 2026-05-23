import 'dart:async';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/material.dart';
import '../../../services/moderator_service.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:record/record.dart';
import 'package:audioplayers/audioplayers.dart';
import 'package:flutter_image_compress/flutter_image_compress.dart';
import 'package:image_picker/image_picker.dart';
import 'package:path_provider/path_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../models/chat_message.dart';
import '../../config/prefs_keys.dart';
import '../../core/di/service_locator.dart';
import '../../services/chat_service.dart';
import '../../services/purchase_service.dart';
import '../../config/api_config.dart';
import '../../features/chat/presentation/widgets/typing_indicator.dart';
import '../../features/chat/presentation/widgets/chat_message_bubble.dart';
import '../../features/chat/presentation/widgets/chat_input_bar.dart';
import '../../core/widgets/neptun_shimmer.dart';
import '../../features/chat/presentation/widgets/chat_animated_message_item.dart';

/// Full native chat messenger — replaces the old WebView chat.
class ChatTab extends StatefulWidget {
  const ChatTab({super.key});

  @override
  State<ChatTab> createState() => _ChatTabState();
}

class _ChatTabState extends State<ChatTab> with AutomaticKeepAliveClientMixin {
  final _chat = sl<ChatService>();
  final _scrollController = ScrollController();
  final _textController = TextEditingController();
  final _nickController = TextEditingController();
  final _focusNode = FocusNode();
  final _searchController = TextEditingController();
  final _searchFocusNode = FocusNode();

  List<ChatMessage> _messages = [];
  bool _searchMode = false;
  String _searchQuery = '';
  List<int> _searchResults = [];
  int _searchCurrentIndex = 0;
  List<String> _typingUsers = [];
  bool _loading = true;
  bool _loadingMore = false;
  bool _hasMoreHistory = true;
  bool _showScrollFab = false;
  int _unreadCount = 0;
  ChatMessage? _replyTo;
  ChatMessage? _editingMessage;
  bool _isTyping = false;
  Timer? _typingTimer;

  // Registration state
  bool _ageConfirmed = false;
  int? _ageGateBirthYear; // null = not selected yet
  bool _rulesAgreed = false;
  bool _needsRegistration = true;
  bool _nickChecking = false;
  String? _nickError;

  // Voice recording
  final AudioRecorder _recorder = AudioRecorder();
  bool _isRecording = false;
  bool _isSending = false;
  Timer? _recordingTimer;
  int _recordingSeconds = 0;

  // Voice playback
  final AudioPlayer _audioPlayer = AudioPlayer();
  String? _playingMessageId;
  bool _isPlaying = false;

  // Sub list
  final List<StreamSubscription> _subs = [];

  @override
  bool get wantKeepAlive => true;

  @override
  void initState() {
    super.initState();

    // All stream subscriptions tracked in _subs for proper disposal
    _subs.add(_chat.newMessageStream.listen(_onNewMessage));
    _subs.add(_chat.deleteStream.listen(_onDeleteMessage));
    _subs.add(_chat.reactionStream.listen(_onReaction));
    _subs.add(_chat.editStream.listen(_onEditMessage));
    _subs.add(
      _chat.typingStream.listen((users) {
        if (mounted) {
          setState(() {
            _typingUsers = users.where((u) => u != _chat.nickname).toList();
          });
        }
      }),
    );
    _subs.add(
      _chat.onlineStream.listen((_) {
        if (mounted) setState(() {});
      }),
    );
    _subs.add(
      _chat.banStatusStream.listen((banned) {
        if (mounted) setState(() {});
      }),
    );
    _subs.add(
      _chat.pendingResolvedStream.listen((event) {
        if (!mounted) return;
        setState(() {
          final idx = _messages.indexWhere((m) => m.id == event.pendingId);
          if (idx != -1) {
            _messages[idx] = event.message;
          } else if (!_messages.any((m) => m.id == event.message.id)) {
            _messages.insert(0, event.message);
          }
        });
      }),
    );
    _subs.add(
      _chat.pendingIdsStream.listen((_) {
        if (mounted) setState(() {});
      }),
    );
    _subs.add(
      Connectivity().onConnectivityChanged.listen((results) async {
        final hasConnection = results.any(
          (r) => r == ConnectivityResult.mobile || r == ConnectivityResult.wifi,
        );
        if (hasConnection) await _chat.flushOfflineQueue();
        if (mounted) setState(() {});
      }),
    );
    _subs.add(
      _chat.errorStream.listen((error) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(error),
              backgroundColor: Theme.of(context).colorScheme.error,
              behavior: SnackBarBehavior.floating,
              duration: const Duration(seconds: 2),
            ),
          );
        }
      }),
    );
    // Listen for moderator state changes
    _subs.add(
      ModeratorService.instance.stream.listen((isMod) {
        if (mounted) {
          setState(() {
            _chat.syncModeratorState();
          });
        }
      }),
    );

    // Audio player complete listener (subscribe once)
    _subs.add(
      _audioPlayer.onPlayerComplete.listen((_) {
        if (mounted) {
          setState(() {
            _isPlaying = false;
            _playingMessageId = null;
          });
        }
      }),
    );

    // Scroll listener for FAB
    _scrollController.addListener(_onScroll);

    // Search
    _searchController.addListener(_updateSearchResults);

    _initChat();
  }

  void _updateSearchResults() {
    final q = _searchController.text.trim().toLowerCase();
    if (q.isEmpty) {
      if (mounted) {
        setState(() {
          _searchQuery = '';
          _searchResults = [];
          _searchCurrentIndex = 0;
        });
      }
      return;
    }
    final results = <int>[];
    for (var i = 0; i < _messages.length; i++) {
      final m = _messages[i];
      if (m.message.toLowerCase().contains(q)) results.add(i);
    }
    if (mounted) {
      setState(() {
        _searchQuery = q;
        _searchResults = results;
        _searchCurrentIndex = results.isNotEmpty ? 0 : -1;
      });
    }
  }

  void _goToSearchResult(int delta) {
    if (_searchResults.isEmpty) return;
    var idx = _searchCurrentIndex + delta;
    if (idx < 0) idx = _searchResults.length - 1;
    if (idx >= _searchResults.length) idx = 0;
    setState(() => _searchCurrentIndex = idx);
    _scrollToMessageIndex(_searchResults[idx]);
  }

  void _scrollToMessageIndex(int listIndex) {
    if (!_scrollController.hasClients) return;
    const itemHeight = 72.0;
    final offset = (_messages.length - 1 - listIndex) * itemHeight;
    _scrollController.animateTo(
      offset.clamp(0.0, _scrollController.position.maxScrollExtent),
      duration: const Duration(milliseconds: 300),
      curve: Curves.easeOutCubic,
    );
  }

  Future<void> _loadMessages() async {
    final messages = await _chat.fetchMessages();
    final filtered = messages.where((m) => !_chat.isBlocked(m.userId)).toList();
    if (mounted) setState(() => _messages = filtered);
  }

  Future<void> _initChat() async {
    if (_chat.deviceId == null) {
      await _chat.init();
    }
    await _chat.loadBlockList();

    debugPrint(
      '🔍 Chat init: nickname=${_chat.nickname}, deviceId=${_chat.deviceId}',
    );

    final messages = await _chat.fetchMessages();
    debugPrint('💬 Chat fetched ${messages.length} messages');

    _chat.connectSSE();

    final filtered = messages.where((m) => !_chat.isBlocked(m.userId)).toList();

    if (mounted) {
      final prefs = await SharedPreferences.getInstance();
      await _chat.restorePendingFromQueue();
      final queue = await _chat.getOfflineQueue();
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
            userId: _chat.nickname ?? 'Ви',
            deviceId: _chat.deviceId ?? '',
            message: text,
            timestamp: (DateTime.now().millisecondsSinceEpoch / 1000).round(),
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
      setState(() {
        _messages = [...synthetics, ...filtered];
        _ageConfirmed = prefs.getBool(PrefsKeys.chatAgeConfirmed) ?? false;
        _rulesAgreed = prefs.getBool(PrefsKeys.chatRulesAgreed) ?? false;
        _needsRegistration = _chat.nickname == null;
        _loading = false;
      });
      final results = await Connectivity().checkConnectivity();
      final hasConnection = results.any(
        (r) => r == ConnectivityResult.mobile || r == ConnectivityResult.wifi,
      );
      if (hasConnection) await _chat.flushOfflineQueue();
    }

    if (filtered.isEmpty && mounted) {
      await Future.delayed(const Duration(seconds: 2));
      if (!mounted) return;
      final retry = await _chat.fetchMessages();
      debugPrint('🔄 Chat retry: ${retry.length} messages');
      final retryFiltered = retry
          .where((m) => !_chat.isBlocked(m.userId))
          .toList();
      if (retryFiltered.isNotEmpty && mounted) {
        final queue = await _chat.getOfflineQueue();
        final synthetics = <ChatMessage>[];
        for (var i = queue.length - 1; i >= 0; i--) {
          final item = queue[i];
          final pid = item['pendingId']?.toString() ?? '';
          final txt = item['text']?.toString() ?? '';
          if (pid.isEmpty || txt.isEmpty) continue;
          synthetics.add(
            ChatMessage(
              id: pid,
              userId: _chat.nickname ?? 'Ви',
              deviceId: _chat.deviceId ?? '',
              message: txt,
              timestamp: (DateTime.now().millisecondsSinceEpoch / 1000).round(),
              isPro: PurchaseService().isPremium,
            ),
          );
        }
        setState(() => _messages = [...synthetics, ...retryFiltered]);
      }
    }
  }

  void _onScroll() {
    final isAtBottom = _scrollController.offset < 100;
    if (_showScrollFab == isAtBottom) {
      setState(() => _showScrollFab = !isAtBottom);
      if (isAtBottom) _unreadCount = 0;
    }
    // Load more when scrolled near top (older messages)
    if (_hasMoreHistory && !_loadingMore && _messages.isNotEmpty) {
      final pos = _scrollController.position;
      if (pos.pixels > pos.maxScrollExtent - 200) {
        _loadMoreMessages();
      }
    }
  }

  Future<void> _loadMoreMessages() async {
    if (_loadingMore || !_hasMoreHistory || _messages.isEmpty) return;
    final oldest = _messages.last;
    // Timestamp can be in ms (from model) — API expects seconds
    final beforeSec = oldest.timestamp < 10000000000
        ? oldest.timestamp
        : (oldest.timestamp / 1000).round();
    setState(() => _loadingMore = true);
    final older = await _chat.fetchMoreMessages(beforeSec);
    final filtered = older
        .where((m) => !_chat.isBlocked(m.userId))
        .where((m) => !_messages.any((x) => x.id == m.id))
        .toList();
    if (mounted) {
      final addedCount = filtered.length;
      setState(() {
        _messages.addAll(filtered);
        _loadingMore = false;
        if (addedCount < 50) _hasMoreHistory = false;
      });
      if (_searchMode && _searchController.text.trim().isNotEmpty) {
        _updateSearchResults();
      }
      // Preserve scroll position when prepending older messages
      if (addedCount > 0 && _scrollController.hasClients) {
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (!_scrollController.hasClients) return;
          const estimatedItemHeight = 72.0;
          _scrollController.jumpTo(
            _scrollController.offset + addedCount * estimatedItemHeight,
          );
        });
      }
    } else {
      setState(() => _loadingMore = false);
    }
  }

  void _onNewMessage(ChatMessage msg) {
    if (!mounted) return;
    if (_messages.any((m) => m.id == msg.id)) return;
    if (_chat.isBlocked(msg.userId)) return;
    setState(() {
      _messages.insert(0, msg);
      if (_messages.length > 200) _messages.removeLast();
    });
    final isAtBottom =
        !_scrollController.hasClients || _scrollController.offset < 100;
    if (isAtBottom) {
      _scrollToBottom();
    } else {
      setState(() => _unreadCount++);
    }
  }

  void _onDeleteMessage(String id) {
    if (!mounted) return;
    setState(() {
      _messages.removeWhere((m) => m.id == id);
    });
  }

  void _onReaction(
    ({String messageId, Map<String, List<ReactionInfo>> reactions}) event,
  ) {
    if (!mounted) return;
    setState(() {
      final idx = _messages.indexWhere((m) => m.id == event.messageId);
      if (idx != -1) {
        _messages[idx] = _messages[idx].copyWithReactions(event.reactions);
      }
    });
  }

  void _onEditMessage(ChatMessage edited) {
    if (!mounted) return;
    setState(() {
      final idx = _messages.indexWhere((m) => m.id == edited.id);
      if (idx != -1) {
        _messages[idx] = edited;
      }
      if (_editingMessage?.id == edited.id) {
        _editingMessage = null;
        _textController.clear();
      }
    });
  }

  void _scrollToBottom() {
    if (_scrollController.hasClients) {
      _scrollController.animateTo(
        0,
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeOut,
      );
    }
    _unreadCount = 0;
  }

  // ── Send message ──────────────────────────────────────────────────────
  Future<void> _send() async {
    final text = _textController.text.trim();
    if (text.isEmpty) return;

    HapticFeedback.lightImpact();

    // Edit mode: PATCH existing message
    final editing = _editingMessage;
    if (editing != null) {
      setState(() => _editingMessage = null);
      _textController.clear();
      _focusNode.requestFocus();
      _onTypingChanged(false);
      setState(() => _isSending = true);
      final updated = await _chat.editMessage(editing.id, text);
      if (mounted) {
        setState(() => _isSending = false);
        if (updated != null) {
          final idx = _messages.indexWhere((m) => m.id == editing.id);
          if (idx != -1) _messages[idx] = updated;
        }
      }
      return;
    }

    _textController.clear();
    _focusNode.requestFocus();

    final replyTo = _replyTo;
    final replyId = _replyTo?.id;
    setState(() => _replyTo = null);

    // Stop typing
    _onTypingChanged(false);

    // Optimistic update: show message immediately so user sees it even if
    // server response is delayed or malformed (e.g. HTML error page)
    final pendingId = 'pending-${DateTime.now().millisecondsSinceEpoch}';
    final nowSec = DateTime.now().millisecondsSinceEpoch / 1000;
    final optimistic = ChatMessage(
      id: pendingId,
      userId: _chat.nickname ?? 'Ви',
      deviceId: _chat.deviceId ?? '',
      message: text,
      timestamp: nowSec.round(),
      replyTo: replyTo != null
          ? ReplyInfo(
              id: replyTo.id,
              nickname: replyTo.userId,
              text: replyTo.message,
            )
          : null,
      isPro: PurchaseService().isPremium,
    );
    if (mounted) {
      setState(() {
        _messages.insert(0, optimistic);
        if (_messages.length > 200) _messages.removeLast();
      });
      _scrollToBottom();
    }

    final sent = await _chat.sendMessage(text, replyToId: replyId);
    if (!mounted) return;
    if (sent != null) {
      setState(() {
        _messages.removeWhere((m) => m.id == pendingId);
      });
      _onNewMessage(sent);
      _scrollToBottom();
    } else {
      await _chat.addToOfflineQueue(
        pendingId: pendingId,
        text: text,
        replyToId: replyId,
      );
      if (mounted) setState(() {});
    }
  }

  void _onTypingChanged(bool typing) {
    if (typing == _isTyping) return;
    _isTyping = typing;
    _chat.sendTyping(typing);
    _typingTimer?.cancel();
    if (typing) {
      _typingTimer = Timer(const Duration(seconds: 4), () {
        _isTyping = false;
        _chat.sendTyping(false);
      });
    }
  }

  // ── Voice recording methods ────────────────────────────────────────────
  Future<void> _startRecording() async {
    try {
      if (!await _recorder.hasPermission()) return;

      // Haptic feedback — user feels the recording start
      HapticFeedback.mediumImpact();

      final dir = await getTemporaryDirectory();
      final path =
          '${dir.path}/voice_${DateTime.now().millisecondsSinceEpoch}.m4a';

      await _recorder.start(
        const RecordConfig(encoder: AudioEncoder.aacLc, bitRate: 128000),
        path: path,
      );

      setState(() {
        _isRecording = true;
        _recordingSeconds = 0;
      });

      _recordingTimer = Timer.periodic(const Duration(seconds: 1), (_) {
        if (mounted) setState(() => _recordingSeconds++);
        if (_recordingSeconds >= 60) _stopAndSendRecording();
      });
    } catch (e) {
      debugPrint('❌ Recording start error: $e');
    }
  }

  Future<void> _cancelRecording() async {
    _recordingTimer?.cancel();
    try {
      await _recorder.stop();
    } catch (_) {}
    if (mounted) {
      setState(() {
        _isRecording = false;
        _recordingSeconds = 0;
      });
    }
  }

  Future<void> _stopAndSendRecording() async {
    _recordingTimer?.cancel();
    if (!_isRecording) return;

    final duration = _recordingSeconds;
    setState(() {
      _isRecording = false;
      _recordingSeconds = 0;
    });

    if (duration < 1) return; // too short

    try {
      final path = await _recorder.stop();
      if (path == null) return;

      setState(() => _isSending = true);
      final sent = await _chat.sendVoiceMessage(path, duration);
      if (sent != null && mounted) {
        _onNewMessage(sent);
        _scrollToBottom();
      }
    } catch (e) {
      debugPrint('❌ Voice send error: $e');
    }
    if (mounted) setState(() => _isSending = false);
  }

  // ── Attach image ─────────────────────────────────────────────────────
  Future<void> _onAttach() async {
    HapticFeedback.lightImpact();
    final source = await showModalBottomSheet<ImageSource>(
      context: context,
      builder: (ctx) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.photo_library_rounded),
              title: const Text('Галерея'),
              onTap: () => Navigator.pop(ctx, ImageSource.gallery),
            ),
            ListTile(
              leading: const Icon(Icons.camera_alt_rounded),
              title: const Text('Камера'),
              onTap: () => Navigator.pop(ctx, ImageSource.camera),
            ),
          ],
        ),
      ),
    );
    if (source == null || !mounted) return;

    try {
      final picker = ImagePicker();
      final xFile = await picker.pickImage(
        source: source,
        maxWidth: 1920,
        imageQuality: 85,
      );
      if (xFile == null || !mounted) return;

      setState(() => _isSending = true);
      final caption = _textController.text.trim();
      if (caption.isNotEmpty) _textController.clear();

      // Convert HEIC/other formats to JPEG (iOS often uses HEIC)
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
      final pathToSend = compressed?.path ?? xFile.path;

      final sent = await _chat.sendImageMessage(
        pathToSend,
        caption: caption.isEmpty ? null : caption,
      );
      if (sent != null && mounted) {
        _onNewMessage(sent);
        _scrollToBottom();
      }
    } catch (e) {
      debugPrint('❌ Image pick/send error: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Помилка відправки фото'),
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    }
    if (mounted) setState(() => _isSending = false);
  }

  // ── Report & Block ───────────────────────────────────────────────────

  void _reportMessage(ChatMessage msg) {
    showDialog(
      context: context,
      builder: (ctx) {
        String? selectedReason;
        return StatefulBuilder(
          builder: (ctx, setDialogState) => AlertDialog(
            title: Text(
              'Поскаржитись',
              style: GoogleFonts.inter(
                fontSize: 16,
                fontWeight: FontWeight.w600,
              ),
            ),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  'Оберіть причину скарги:',
                  style: GoogleFonts.inter(fontSize: 14),
                ),
                const SizedBox(height: 12),
                ...[
                  'Спам',
                  'Образи або ненависть',
                  'Неправдива інформація',
                  'Загрози або насильство',
                  'Інше',
                ].map(
                  (reason) => RadioListTile<String>(
                    title: Text(reason, style: GoogleFonts.inter(fontSize: 14)),
                    value: reason,
                    // ignore: deprecated_member_use
                    groupValue: selectedReason,
                    // ignore: deprecated_member_use
                    onChanged: (v) => setDialogState(() => selectedReason = v),
                    dense: true,
                  ),
                ),
              ],
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('Скасувати'),
              ),
              FilledButton(
                onPressed: selectedReason == null
                    ? null
                    : () async {
                        Navigator.pop(ctx);
                        await _chat.reportMessage(
                          msg.id,
                          selectedReason!,
                          reportedDeviceId: msg.deviceId,
                          reportedNickname: msg.userId,
                          originalText: msg.message,
                        );
                        if (mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(
                              content: const Text('Скаргу надіслано'),
                              backgroundColor: Colors.green[700],
                              behavior: SnackBarBehavior.floating,
                            ),
                          );
                        }
                      },
                child: const Text('Надіслати'),
              ),
            ],
          ),
        );
      },
    );
  }

  Future<void> _deleteAllMessagesFromUser(ChatMessage msg) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Видалити всі повідомлення'),
        content: Text(
          'Видалити всі повідомлення від ${msg.userId}? Цю дію не можна скасувати.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Скасувати'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: FilledButton.styleFrom(
              backgroundColor: Theme.of(ctx).colorScheme.error,
              foregroundColor: Theme.of(ctx).colorScheme.onError,
            ),
            child: const Text('Видалити всі'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    final deleted = await _chat.deleteAllUserMessages(
      nickname: msg.userId,
      deviceId: msg.deviceId,
    );
    if (mounted) {
      if (deleted != null && deleted > 0) {
        setState(() {
          _messages.removeWhere(
            (m) => m.userId == msg.userId || m.deviceId == msg.deviceId,
          );
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Видалено повідомлень: $deleted'),
            behavior: SnackBarBehavior.floating,
          ),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Не вдалося видалити'),
            backgroundColor: Colors.red,
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    }
  }

  Future<void> _banChatUser(ChatMessage msg) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(
          'Заблокувати в чаті?',
          style: GoogleFonts.inter(fontSize: 16, fontWeight: FontWeight.w600),
        ),
        content: Text(
          '${msg.userId} не зможе надсилати повідомлення.',
          style: GoogleFonts.inter(fontSize: 14),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Скасувати'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Заблокувати'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;

    final result = await _chat.banUser(
      msg.userId,
      targetDeviceId: msg.deviceId.isNotEmpty ? msg.deviceId : null,
    );
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          result.success
              ? '${msg.userId} заблоковано'
              : (result.error ?? 'Не вдалося заблокувати'),
        ),
        behavior: SnackBarBehavior.floating,
        backgroundColor: result.success ? null : Theme.of(context).colorScheme.error,
      ),
    );
  }

  void _blockUser(ChatMessage msg) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(
          'Сховати користувача?',
          style: GoogleFonts.inter(fontSize: 16, fontWeight: FontWeight.w600),
        ),
        content: Text(
          'Повідомлення від ${msg.userId} більше не відображатимуться. '
          'Цю дію можна скасувати в налаштуваннях.',
          style: GoogleFonts.inter(fontSize: 14),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Скасувати'),
          ),
          FilledButton(
            onPressed: () {
              Navigator.pop(ctx);
              _chat.blockUser(msg.userId);
              if (mounted) {
                setState(() {
                  _messages.removeWhere((m) => m.userId == msg.userId);
                });
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text('${msg.userId} приховано'),
                    behavior: SnackBarBehavior.floating,
                    action: SnackBarAction(
                      label: 'Скасувати',
                      onPressed: () {
                        _chat.unblockUser(msg.userId);
                        _loadMessages();
                      },
                    ),
                  ),
                );
              }
            },
            child: const Text('Сховати'),
          ),
        ],
      ),
    );
  }

  // ── Voice playback methods ────────────────────────────────────────────
  Future<void> _togglePlayback(String messageId, String url) async {
    if (_playingMessageId == messageId && _isPlaying) {
      await _audioPlayer.pause();
      if (mounted) setState(() => _isPlaying = false);
      return;
    }

    // Ensure full URL (server stores relative paths like /data/audio/...)
    final fullUrl = url.startsWith('http') ? url : '${ApiConfig.baseUrl}$url';
    debugPrint('🔊 Playing voice: $fullUrl');

    try {
      if (_playingMessageId != messageId) {
        await _audioPlayer.stop();
        await _audioPlayer.play(UrlSource(fullUrl));
      } else {
        await _audioPlayer.resume();
      }
      if (mounted) {
        setState(() {
          _playingMessageId = messageId;
          _isPlaying = true;
        });
      }
    } catch (e) {
      debugPrint('❌ Playback error: $e');
      if (mounted) {
        setState(() {
          _isPlaying = false;
          _playingMessageId = null;
        });
      }
    }
  }

  // ── Nickname registration ──────────────────────────────────────────────
  Future<void> _registerNickname() async {
    final nick = _nickController.text.trim();
    if (nick.length < 2 || nick.length > 20) {
      setState(() => _nickError = 'Від 2 до 20 символів');
      return;
    }

    setState(() {
      _nickChecking = true;
      _nickError = null;
    });

    final check = await _chat.checkNickname(nick);
    if (!check.available) {
      if (mounted) {
        setState(() {
          _nickChecking = false;
          _nickError = check.error;
        });
      }
      return;
    }

    final result = await _chat.registerNickname(nick);
    if (mounted) {
      setState(() => _nickChecking = false);
      if (result.success) {
        // Fetch messages now that we have a nickname
        final messages = await _chat.fetchMessages();
        if (mounted) {
          setState(() {
            _needsRegistration = false;
            _messages = messages;
          });
        }
      } else {
        setState(() => _nickError = result.error);
      }
    }
  }

  @override
  void dispose() {
    for (final sub in _subs) {
      sub.cancel();
    }
    _scrollController.dispose();
    _textController.dispose();
    _nickController.dispose();
    _focusNode.dispose();
    _searchController.dispose();
    _searchFocusNode.dispose();
    _typingTimer?.cancel();
    _recordingTimer?.cancel();
    _recorder.dispose();
    _audioPlayer.dispose();
    _chat.disconnectSSE();
    super.dispose();
  }

  // ═══════════════════════════════════════════════════════════════════════
  // BUILD
  // ═══════════════════════════════════════════════════════════════════════
  @override
  Widget build(BuildContext context) {
    super.build(context);

    final cs = Theme.of(context).colorScheme;

    if (_loading) return _buildLoading();
    if (!_ageConfirmed) return _buildAgeGate();
    if (_needsRegistration) return _buildRegistration();
    if (!_rulesAgreed) return _buildRulesAgreement();
    if (_chat.isBanned) return _buildBanned();

    return GestureDetector(
      onTap: () => FocusScope.of(context).unfocus(),
      onHorizontalDragEnd: (details) {
        // Swipe right to dismiss keyboard
        if ((details.primaryVelocity ?? 0) > 300) {
          FocusScope.of(context).unfocus();
        }
      },
      child: Scaffold(
        backgroundColor: cs.surface,
        body: Column(
          children: [
            _buildChatHeader(),
            Expanded(child: _buildMessageList()),
            _buildTypingIndicator(),
            ChatInputBar(
              textController: _textController,
              focusNode: _focusNode,
              replyTo: _replyTo,
              editTo: _editingMessage,
              isSending: _isSending,
              isRecording: _isRecording,
              recordingSeconds: _recordingSeconds,
              onReplyDismiss: () => setState(() => _replyTo = null),
              onEditDismiss: () => setState(() => _editingMessage = null),
              onTypingChanged: _onTypingChanged,
              onSend: _send,
              onStartRecording: _startRecording,
              onCancelRecording: _cancelRecording,
              onStopAndSendRecording: _stopAndSendRecording,
              onAttach: _onAttach,
            ),
          ],
        ),
        floatingActionButton: _showScrollFab ? _buildScrollFab() : null,
      ),
    );
  }

  // ── Loading ────────────────────────────────────────────────────────────
  Widget _buildLoading() {
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      backgroundColor: cs.surface,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              NeptunShimmer(width: 140, height: 20, borderRadius: 6),
              const SizedBox(height: 32),
              // Skeleton messages (alternating)
              const Align(
                alignment: Alignment.centerLeft,
                child: NeptunShimmer(width: 200, height: 48, borderRadius: 18),
              ),
              const SizedBox(height: 12),
              Align(
                alignment: Alignment.centerRight,
                child: NeptunShimmer(width: 180, height: 40, borderRadius: 18),
              ),
              const SizedBox(height: 12),
              const Align(
                alignment: Alignment.centerLeft,
                child: NeptunShimmer(width: 160, height: 44, borderRadius: 18),
              ),
              const SizedBox(height: 24),
              Center(
                child: Text(
                  'Завантаження чату...',
                  style: TextStyle(color: cs.onSurfaceVariant, fontSize: 13),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ── Age gate (16+) ────────────────────────────────────────────────────
  static const int _minChatAge = 16;

  Widget _buildAgeGate() {
    final cs = Theme.of(context).colorScheme;
    final currentYear = DateTime.now().year;
    final minBirthYear = currentYear - 100;
    final maxBirthYear =
        currentYear - 5; // включно молодші, щоб було що відсікати
    final birthYears = List.generate(
      maxBirthYear - minBirthYear + 1,
      (i) => maxBirthYear - i,
    );

    return Scaffold(
      backgroundColor: cs.surface,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(32),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  Icons.cake_outlined,
                  size: 56,
                  color: cs.primary.withValues(alpha: 0.8),
                ),
                const SizedBox(height: 24),
                Text(
                  'Чат лише для користувачів $_minChatAge+',
                  textAlign: TextAlign.center,
                  style: GoogleFonts.inter(
                    fontSize: 18,
                    fontWeight: FontWeight.w600,
                    color: cs.onSurface,
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  'Оберіть рік народження. Чат захищено віковим порогом '
                  'для безпеки всіх учасників.',
                  textAlign: TextAlign.center,
                  style: GoogleFonts.inter(
                    fontSize: 14,
                    color: cs.onSurfaceVariant,
                  ),
                ),
                const SizedBox(height: 24),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  decoration: BoxDecoration(
                    color: cs.surfaceContainerHighest.withValues(alpha: 0.5),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(
                      color: cs.outline.withValues(alpha: 0.3),
                    ),
                  ),
                  child: DropdownButtonHideUnderline(
                    child: DropdownButton<int>(
                      value: _ageGateBirthYear,
                      isExpanded: true,
                      hint: Text(
                        'Рік народження',
                        style: GoogleFonts.inter(color: cs.onSurfaceVariant),
                      ),
                      items: birthYears.map((year) {
                        return DropdownMenuItem(
                          value: year,
                          child: Text(
                            '$year (${currentYear - year} років)',
                            style: GoogleFonts.inter(color: cs.onSurface),
                          ),
                        );
                      }).toList(),
                      onChanged: (v) {
                        if (mounted) setState(() => _ageGateBirthYear = v);
                      },
                    ),
                  ),
                ),
                const SizedBox(height: 24),
                FilledButton(
                  onPressed: _ageGateBirthYear == null
                      ? null
                      : () async {
                          final year = _ageGateBirthYear!;
                          final age = currentYear - year;
                          if (age < _minChatAge) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(
                                content: Text(
                                  'Чат доступний лише з $_minChatAge років. '
                                  'Вам зараз $age.',
                                ),
                                backgroundColor: cs.error,
                                behavior: SnackBarBehavior.floating,
                              ),
                            );
                            return;
                          }
                          final prefs = await SharedPreferences.getInstance();
                          await prefs.setBool(PrefsKeys.chatAgeConfirmed, true);
                          if (mounted) setState(() => _ageConfirmed = true);
                        },
                  style: FilledButton.styleFrom(
                    minimumSize: const Size(double.infinity, 48),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(14),
                    ),
                  ),
                  child: const Text('Продовжити'),
                ),
                const SizedBox(height: 16),
                Text(
                  'Якщо вам немає $_minChatAge років — чат недоступний.',
                  textAlign: TextAlign.center,
                  style: GoogleFonts.inter(
                    fontSize: 12,
                    color: cs.onSurfaceVariant.withValues(alpha: 0.8),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  // ── Rules agreement ───────────────────────────────────────────────────
  Widget _buildRulesAgreement() {
    final cs = Theme.of(context).colorScheme;
    const rules = '''
• Поважайте інших учасників — заборонено образи, погрози, дискримінацію.
• Заборонено спам, рекламу, поширення неперевіреної інформації.
• Не діліться персональними даними своїми чи чужими.
• Адмін може видалити повідомлення або заблокувати порушників.
• Порушення правил призводить до попередження або блокування.
''';
    return Scaffold(
      backgroundColor: cs.surface,
      appBar: AppBar(
        title: Text(
          'Правила чату',
          style: GoogleFonts.inter(fontWeight: FontWeight.w600, fontSize: 18),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              rules.trim(),
              style: GoogleFonts.inter(
                fontSize: 15,
                color: cs.onSurface,
                height: 1.6,
              ),
            ),
            const SizedBox(height: 24),
            FilledButton(
              onPressed: () async {
                final prefs = await SharedPreferences.getInstance();
                await prefs.setBool(PrefsKeys.chatRulesAgreed, true);
                if (mounted) setState(() => _rulesAgreed = true);
              },
              style: FilledButton.styleFrom(
                minimumSize: const Size(double.infinity, 48),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14),
                ),
              ),
              child: const Text('Я ознайомився з правилами'),
            ),
          ],
        ),
      ),
    );
  }

  // ── Registration ──────────────────────────────────────────────────────
  Widget _buildRegistration() {
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      backgroundColor: cs.surface,
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 80,
                height: 80,
                decoration: BoxDecoration(
                  color: cs.primary.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(24),
                ),
                child: Icon(Icons.chat_rounded, size: 40, color: cs.primary),
              ),
              const SizedBox(height: 24),
              Text(
                'Вітаємо в чаті!',
                style: GoogleFonts.inter(
                  fontSize: 24,
                  fontWeight: FontWeight.w700,
                  color: cs.onSurface,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Оберіть нікнейм для спілкування',
                style: GoogleFonts.inter(
                  fontSize: 15,
                  color: cs.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 32),
              TextField(
                controller: _nickController,
                maxLength: 20,
                style: GoogleFonts.inter(color: cs.onSurface, fontSize: 16),
                decoration: InputDecoration(
                  hintText: 'Ваш нікнейм',
                  hintStyle: GoogleFonts.inter(
                    color: cs.onSurface.withValues(alpha: 0.35),
                  ),
                  errorText: _nickError,
                  counterStyle: GoogleFonts.inter(
                    color: cs.onSurface.withValues(alpha: 0.35),
                    fontSize: 12,
                  ),
                  filled: true,
                  fillColor: cs.surfaceContainer,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(16),
                    borderSide: BorderSide(color: cs.outline),
                  ),
                  enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(16),
                    borderSide: BorderSide(color: cs.outline),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(16),
                    borderSide: BorderSide(color: cs.primary, width: 1.5),
                  ),
                  errorBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(16),
                    borderSide: BorderSide(color: cs.error),
                  ),
                  contentPadding: const EdgeInsets.symmetric(
                    horizontal: 20,
                    vertical: 16,
                  ),
                ),
                onSubmitted: (_) => _registerNickname(),
              ),
              const SizedBox(height: 20),
              SizedBox(
                width: double.infinity,
                height: 52,
                child: ElevatedButton(
                  onPressed: _nickChecking ? null : _registerNickname,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: cs.primary,
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                    elevation: 0,
                  ),
                  child: _nickChecking
                      ? const SizedBox(
                          width: 22,
                          height: 22,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white,
                          ),
                        )
                      : Text(
                          'Почати',
                          style: GoogleFonts.inter(
                            fontSize: 16,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ── Banned ─────────────────────────────────────────────────────────────
  Widget _buildBanned() {
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      backgroundColor: cs.surface,
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 80,
                height: 80,
                decoration: BoxDecoration(
                  color: cs.error.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(24),
                ),
                child: Icon(Icons.block_rounded, size: 40, color: cs.error),
              ),
              const SizedBox(height: 24),
              Text(
                'Вас заблоковано',
                style: GoogleFonts.inter(
                  fontSize: 22,
                  fontWeight: FontWeight.w700,
                  color: cs.onSurface,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                _chat.banReason ?? 'Порушення правил',
                style: GoogleFonts.inter(
                  fontSize: 15,
                  color: cs.onSurfaceVariant,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 32),
              TextButton.icon(
                onPressed: () async {
                  await _chat.checkBanStatus();
                  if (mounted && !_chat.isBanned) {
                    setState(() {});
                    // _loadChat(); // removed: not needed for moderator state sync
                  }
                },
                icon: const Icon(Icons.refresh_rounded),
                label: const Text('Перевірити'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ── AppBar ─────────────────────────────────────────────────────────────
  Widget _buildChatHeader() {
    final cs = Theme.of(context).colorScheme;
    if (!_searchMode) return const SizedBox.shrink();
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
      decoration: BoxDecoration(
        color: const Color(0xFF111821),
        border: Border(
          bottom: BorderSide(color: cs.outline.withValues(alpha: 0.25)),
        ),
      ),
      child: _buildSearchBar(),
    );
  }

  Widget _buildSearchBar() {
    final cs = Theme.of(context).colorScheme;
    return Row(
      children: [
        GestureDetector(
          onTap: () {
            HapticFeedback.lightImpact();
            FocusScope.of(context).unfocus();
            setState(() {
              _searchMode = false;
              _searchController.clear();
              _searchQuery = '';
              _searchResults = [];
            });
          },
          child: Icon(
            Icons.arrow_back_ios_rounded,
            color: cs.onSurfaceVariant,
            size: 20,
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: TextField(
            controller: _searchController,
            focusNode: _searchFocusNode,
            style: GoogleFonts.inter(fontSize: 15),
            decoration: InputDecoration(
              hintText: 'Пошук у чаті',
              hintStyle: GoogleFonts.inter(
                fontSize: 15,
                color: cs.onSurfaceVariant.withValues(alpha: 0.6),
              ),
              border: InputBorder.none,
              contentPadding: const EdgeInsets.symmetric(vertical: 8),
              isDense: true,
            ),
            onSubmitted: (_) {
              if (_searchResults.isNotEmpty) _goToSearchResult(0);
            },
          ),
        ),
        if (_searchQuery.isNotEmpty) ...[
          if (_searchResults.isEmpty)
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: Text(
                'Нічого не знайдено',
                style: GoogleFonts.inter(
                  fontSize: 12,
                  color: cs.onSurfaceVariant.withValues(alpha: 0.7),
                ),
              ),
            )
          else ...[
            Text(
              '${_searchCurrentIndex + 1}/${_searchResults.length}',
              style: GoogleFonts.inter(
                fontSize: 12,
                color: cs.onSurfaceVariant,
              ),
            ),
            const SizedBox(width: 4),
            IconButton(
              icon: const Icon(Icons.keyboard_arrow_up_rounded),
              onPressed: () => _goToSearchResult(-1),
              style: IconButton.styleFrom(
                minimumSize: const Size(36, 36),
                padding: EdgeInsets.zero,
              ),
            ),
            IconButton(
              icon: const Icon(Icons.keyboard_arrow_down_rounded),
              onPressed: () => _goToSearchResult(1),
              style: IconButton.styleFrom(
                minimumSize: const Size(36, 36),
                padding: EdgeInsets.zero,
              ),
            ),
          ],
        ],
      ],
    );
  }

  // ── Message List ──────────────────────────────────────────────────────
  Widget _buildMessageList() {
    final cs = Theme.of(context).colorScheme;
    if (_messages.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.forum_rounded,
              size: 48,
              color: cs.onSurface.withValues(alpha: 0.2),
            ),
            const SizedBox(height: 12),
            Text(
              'Поки що пусто',
              style: GoogleFonts.inter(
                fontSize: 16,
                color: cs.onSurface.withValues(alpha: 0.35),
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'Напишіть перше повідомлення!',
              style: GoogleFonts.inter(
                fontSize: 13,
                color: cs.onSurface.withValues(alpha: 0.35),
              ),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      controller: _scrollController,
      reverse: true,
      keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      itemCount: _messages.length + (_loadingMore ? 1 : 0),
      itemBuilder: (context, index) {
        if (index >= _messages.length) {
          return Center(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: SizedBox(
                width: 24,
                height: 24,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: cs.primary,
                ),
              ),
            ),
          );
        }
        final msg = _messages[index];
        final prevMsg = index + 1 < _messages.length
            ? _messages[index + 1]
            : null;
        final nextMsg = index > 0 ? _messages[index - 1] : null;

        // Date divider
        Widget? divider;
        if (prevMsg == null || _differentDay(msg, prevMsg)) {
          divider = _buildDateDivider(msg);
        }

        final isMine = msg.deviceId == _chat.deviceId;
        final isFirstInGroup = nextMsg == null || nextMsg.userId != msg.userId;
        final isLastInGroup = prevMsg == null || prevMsg.userId != msg.userId;

        final bubble = ChatMessageBubble(
          message: msg,
          isMine: isMine,
          isFirstInGroup: isFirstInGroup,
          isLastInGroup: isLastInGroup,
          myDeviceId: _chat.deviceId ?? '',
          isModerator: _chat.isModerator,
          onReply: () => setState(() => _replyTo = msg),
          onReact: (emoji) => _chat.react(msg.id, emoji),
          onDelete: () => _chat.deleteMessage(msg.id),
          onBan: _chat.isModerator
              ? () => _banChatUser(msg)
              : null,
          onReport: isMine ? null : () => _reportMessage(msg),
          onBlock: isMine ? null : () => _blockUser(msg),
          onDeleteAll: _chat.isModerator && !isMine
              ? () => _deleteAllMessagesFromUser(msg)
              : null,
          onCopy: () {
            Clipboard.setData(ClipboardData(text: msg.message));
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text('Скопійовано'),
                behavior: SnackBarBehavior.floating,
                duration: Duration(seconds: 1),
              ),
            );
          },
          onPlayVoice: msg.isVoice ? _togglePlayback : null,
          isPlayingVoice: _playingMessageId == msg.id && _isPlaying,
          searchHighlight:
              _searchQuery.isNotEmpty &&
                  msg.message.toLowerCase().contains(_searchQuery)
              ? _searchQuery
              : null,
          onEdit: isMine && !msg.isVoice
              ? () {
                  setState(() {
                    _editingMessage = msg;
                    _replyTo = null;
                  });
                  _textController.text = msg.message;
                  _textController.selection = TextSelection.collapsed(
                    offset: msg.message.length,
                  );
                  _focusNode.requestFocus();
                }
              : null,
          isPending: isMine && _chat.isPending(msg.id),
        );

        final content = divider != null
            ? Column(children: [bubble, divider])
            : bubble;
        return ChatAnimatedMessageItem(
          messageId: msg.id,
          animate: index == 0,
          child: content,
        );
      },
    );
  }

  bool _differentDay(ChatMessage a, ChatMessage b) {
    final da = a.dateTime;
    final db = b.dateTime;
    return da.year != db.year || da.month != db.month || da.day != db.day;
  }

  Widget _buildDateDivider(ChatMessage msg) {
    final cs = Theme.of(context).colorScheme;
    final d = msg.dateTime;
    final now = DateTime.now();
    String label;
    if (d.year == now.year && d.month == now.month && d.day == now.day) {
      label = 'Сьогодні';
    } else if (d.year == now.year &&
        d.month == now.month &&
        d.day == now.day - 1) {
      label = 'Вчора';
    } else {
      label =
          '${d.day.toString().padLeft(2, '0')}.${d.month.toString().padLeft(2, '0')}.${d.year}';
    }
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Center(
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 5),
          decoration: BoxDecoration(
            color: cs.surfaceContainerHighest,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Text(
            label,
            style: GoogleFonts.inter(
              fontSize: 12,
              fontWeight: FontWeight.w500,
              color: cs.onSurfaceVariant,
            ),
          ),
        ),
      ),
    );
  }

  // ── Typing Indicator ──────────────────────────────────────────────────
  Widget _buildTypingIndicator() {
    final cs = Theme.of(context).colorScheme;
    if (_typingUsers.isEmpty) return const SizedBox.shrink();

    final text = _typingUsers.length == 1
        ? '${_typingUsers.first} друкує...'
        : '${_typingUsers.length} друкують...';

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      alignment: Alignment.centerLeft,
      child: Row(
        children: [
          const ChatTypingIndicator(),
          const SizedBox(width: 8),
          Flexible(
            child: Text(
              text,
              style: GoogleFonts.inter(
                fontSize: 12,
                color: cs.onSurface.withValues(alpha: 0.35),
              ),
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }

  // ── Scroll FAB ─────────────────────────────────────────────────────────
  Widget _buildScrollFab() {
    final cs = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.only(bottom: 70),
      child: FloatingActionButton.small(
        onPressed: _scrollToBottom,
        backgroundColor: cs.surfaceContainerHighest,
        elevation: 4,
        child: Badge(
          isLabelVisible: _unreadCount > 0,
          label: Text(
            '$_unreadCount',
            style: GoogleFonts.inter(fontSize: 10, fontWeight: FontWeight.w600),
          ),
          backgroundColor: cs.primary,
          child: Icon(
            Icons.keyboard_arrow_down_rounded,
            color: cs.onSurface,
            size: 24,
          ),
        ),
      ),
    );
  }
}
