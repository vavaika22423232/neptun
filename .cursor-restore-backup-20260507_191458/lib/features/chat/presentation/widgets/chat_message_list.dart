import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:neptun_alarm_app/config/api_config.dart';
import 'package:neptun_alarm_app/models/chat_message.dart';
import 'package:neptun_alarm_app/core/providers/chat_provider.dart';
import 'package:neptun_alarm_app/features/chat/presentation/providers/chat_controller.dart';
import 'package:neptun_alarm_app/features/chat/presentation/widgets/chat_message_bubble.dart';
import 'package:neptun_alarm_app/services/moderator_service.dart';

class ChatMessageList extends ConsumerStatefulWidget {
  final ScrollController scrollController;
  final String myDeviceId;
  final void Function(ChatMessage) onReply;
  final void Function(ChatMessage) onEdit;
  final void Function(ChatMessage) onReport;
  final void Function(ChatMessage) onBlock;
  final void Function(ChatMessage) onDeleteAll;

  /// Серверний бан у чаті (тільки для модераторів) — [ChatMessageBubble] передає сюди дію з контексту.
  final void Function(ChatMessage)? onBan;

  const ChatMessageList({
    super.key,
    required this.scrollController,
    required this.myDeviceId,
    required this.onReply,
    required this.onEdit,
    required this.onReport,
    required this.onBlock,
    required this.onDeleteAll,
    this.onBan,
  });

  @override
  ConsumerState<ChatMessageList> createState() => ChatMessageListState();
}

class ChatMessageListState extends ConsumerState<ChatMessageList> {
  final Map<String, GlobalKey> _messageKeys = {};

  @override
  void initState() {
    super.initState();
    widget.scrollController.addListener(_onScroll);
  }

  @override
  void dispose() {
    widget.scrollController.removeListener(_onScroll);
    super.dispose();
  }

  void _copyMessageToClipboard(BuildContext context, ChatMessage message) {
    String text;
    if (message.isVoice) {
      text = message.message.trim();
      if (text.isEmpty) {
        text = 'Голосове повідомлення';
      }
    } else if (message.isImage) {
      text = message.message.trim();
      if (text.isEmpty && message.imageUrl != null) {
        text = ApiConfig.resolveAbsoluteUrl(message.imageUrl!);
      }
    } else {
      text = message.message.trim();
    }

    if (text.isEmpty) {
      ScaffoldMessenger.maybeOf(context)?.showSnackBar(
        const SnackBar(
          content: Text('Немає тексту для копіювання'),
          behavior: SnackBarBehavior.floating,
        ),
      );
      return;
    }

    Clipboard.setData(ClipboardData(text: text));
    HapticFeedback.lightImpact();
    ScaffoldMessenger.maybeOf(context)?.showSnackBar(
      const SnackBar(
        content: Text('Скопійовано'),
        behavior: SnackBarBehavior.floating,
        duration: Duration(seconds: 2),
      ),
    );
  }

  void _onScroll() {
    final state = ref.read(chatControllerProvider);
    if (state.hasMoreHistory &&
        !state.isLoadingMore &&
        state.messages.isNotEmpty) {
      final pos = widget.scrollController.position;
      if (pos.pixels > pos.maxScrollExtent - 200) {
        ref.read(chatControllerProvider.notifier).loadMoreMessages();
      }
    }
  }

  // This will be called from ChatTab via a GlobalKey for ChatMessageList
  void scrollToMessageId(String messageId) {
    final key = _messageKeys[messageId];
    if (key != null && key.currentContext != null) {
      Scrollable.ensureVisible(
        key.currentContext!,
        duration: const Duration(milliseconds: 400),
        curve: Curves.easeInOutQuart,
        alignment: 0.5, // Center the message
      );
    } else {
      // Fallback: estimate position if not in tree
      final state = ref.read(chatControllerProvider);
      final index = state.messages.indexWhere((m) => m.id == messageId);
      if (index != -1) {
        final offset = index * 120.0; // Slightly better estimate
        widget.scrollController.animateTo(
          offset.clamp(0, widget.scrollController.position.maxScrollExtent),
          duration: const Duration(milliseconds: 400),
          curve: Curves.easeInOutQuart,
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final listSlice = ref.watch(
      chatControllerProvider.select(
        (s) => (s.messages, s.isLoadingMore, s.playingMessageId, s.isPlaying),
      ),
    );
    final messages = listSlice.$1;
    final isLoadingMore = listSlice.$2;
    final playingMessageId = listSlice.$3;
    final isPlaying = listSlice.$4;

    final chatService = ref.read(chatServiceProvider);
    final isModerator = ModeratorService.instance.isModerator;

    return ListView.builder(
      controller: widget.scrollController,
      padding: const EdgeInsets.symmetric(horizontal: 0, vertical: 8),
      reverse: true,
      physics: const BouncingScrollPhysics(
        parent: AlwaysScrollableScrollPhysics(),
      ),
      keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
      itemCount: messages.length + (isLoadingMore ? 1 : 0),
      itemBuilder: (context, index) {
        if (index == messages.length) {
          return Center(
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: CircularProgressIndicator(
                strokeWidth: 2,
                color: Theme.of(context).colorScheme.primary,
              ),
            ),
          );
        }

        final message = messages[index];
        final myId = widget.myDeviceId.trim();
        final myNick = chatService.nickname?.trim();

        bool msgIsMine(ChatMessage m) {
          final authorNick = m.userId.trim();
          final nickMatch =
              myNick != null &&
              myNick.isNotEmpty &&
              authorNick.toLowerCase() == myNick.toLowerCase();
          return (myId.isNotEmpty &&
                  m.deviceId.trim().isNotEmpty &&
                  m.deviceId == myId) ||
              nickMatch;
        }

        final isMine = msgIsMine(message);

        // Grouping: use isMine boundary + peer userId so «Анонім» from server still groups with own bubbles when deviceId matches.
        final prev = index < messages.length - 1 ? messages[index + 1] : null;
        final next = index > 0 ? messages[index - 1] : null;
        final prevMine = prev != null && msgIsMine(prev);
        final nextMine = next != null && msgIsMine(next);

        final isFirstInGroup =
            prev == null ||
            prevMine != isMine ||
            (!isMine && !prevMine && prev.userId != message.userId);
        final isLastInGroup =
            next == null ||
            nextMine != isMine ||
            (!isMine && !nextMine && next.userId != message.userId);

        // Key management
        final key = _messageKeys.putIfAbsent(message.id, () => GlobalKey());

        return ChatMessageBubble(
          key: key,
          message: message,
          isMine: isMine,
          isFirstInGroup: isFirstInGroup,
          isLastInGroup: isLastInGroup,
          myDeviceId: widget.myDeviceId,
          isModerator: isModerator,
          onReply: () => widget.onReply(message),
          onEdit: () => widget.onEdit(message),
          onReport: () => widget.onReport(message),
          onBlock: () => widget.onBlock(message),
          onBan: isModerator && widget.onBan != null
              ? () => widget.onBan!(message)
              : null,
          onDeleteAll: () => widget.onDeleteAll(message),
          onReact: (emoji) => chatService.react(message.id, emoji),
          onDelete: () => chatService.deleteMessage(message.id),
          onCopy: () => _copyMessageToClipboard(context, message),
          onPlayVoice: (id, url) =>
              ref.read(chatControllerProvider.notifier).togglePlayback(id, url),
          isPlayingVoice: playingMessageId == message.id && isPlaying,
          isPending: message.id.startsWith('pending-'),
        );
      },
    );
  }
}
