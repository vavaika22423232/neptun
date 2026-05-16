import 'package:neptun_alarm_app/models/chat_message.dart';

const Object _chatUnset = Object();

/// Стан глобального чату (під Riverpod [ChatNotifier]).
class ChatState {
  final List<ChatMessage> messages;
  final bool isLoading;
  final bool ageConfirmed;
  final bool rulesAgreed;
  final bool needsRegistration;
  final bool isBanned;
  final String? banReason;
  final int onlineCount;
  final List<String> typingUsers;
  final ChatMessage? editingMessage;
  final ChatMessage? replyTo;
  final bool isLoadingMore;
  final bool hasMoreHistory;
  final bool isSending;
  final bool isRecording;
  final int recordingSeconds;
  final String? playingMessageId;
  final bool isPlaying;
  final bool searchMode;
  final String searchQuery;
  final List<int> searchResults;
  final int searchCurrentIndex;

  const ChatState({
    this.messages = const [],
    this.isLoading = true,
    this.ageConfirmed = false,
    this.rulesAgreed = false,
    this.needsRegistration = true,
    this.isBanned = false,
    this.banReason,
    this.onlineCount = 0,
    this.typingUsers = const [],
    this.editingMessage,
    this.replyTo,
    this.isLoadingMore = false,
    this.hasMoreHistory = true,
    this.isSending = false,
    this.isRecording = false,
    this.recordingSeconds = 0,
    this.playingMessageId,
    this.isPlaying = false,
    this.searchMode = false,
    this.searchQuery = '',
    this.searchResults = const [],
    this.searchCurrentIndex = -1,
  });

  static const initial = ChatState();

  ChatState copyWith({
    List<ChatMessage>? messages,
    bool? isLoading,
    bool? ageConfirmed,
    bool? rulesAgreed,
    bool? needsRegistration,
    bool? isBanned,
    Object? banReason = _chatUnset,
    int? onlineCount,
    List<String>? typingUsers,
    Object? editingMessage = _chatUnset,
    Object? replyTo = _chatUnset,
    bool? isLoadingMore,
    bool? hasMoreHistory,
    bool? isSending,
    bool? isRecording,
    int? recordingSeconds,
    Object? playingMessageId = _chatUnset,
    bool? isPlaying,
    bool? searchMode,
    String? searchQuery,
    List<int>? searchResults,
    int? searchCurrentIndex,
    bool clearEdit = false,
    bool clearReply = false,
  }) {
    return ChatState(
      messages: messages ?? this.messages,
      isLoading: isLoading ?? this.isLoading,
      ageConfirmed: ageConfirmed ?? this.ageConfirmed,
      rulesAgreed: rulesAgreed ?? this.rulesAgreed,
      needsRegistration: needsRegistration ?? this.needsRegistration,
      isBanned: isBanned ?? this.isBanned,
      banReason: identical(banReason, _chatUnset)
          ? this.banReason
          : banReason as String?,
      onlineCount: onlineCount ?? this.onlineCount,
      typingUsers: typingUsers ?? this.typingUsers,
      editingMessage: clearEdit
          ? null
          : (identical(editingMessage, _chatUnset)
                ? this.editingMessage
                : editingMessage as ChatMessage?),
      replyTo: clearReply
          ? null
          : (identical(replyTo, _chatUnset)
                ? this.replyTo
                : replyTo as ChatMessage?),
      isLoadingMore: isLoadingMore ?? this.isLoadingMore,
      hasMoreHistory: hasMoreHistory ?? this.hasMoreHistory,
      isSending: isSending ?? this.isSending,
      isRecording: isRecording ?? this.isRecording,
      recordingSeconds: recordingSeconds ?? this.recordingSeconds,
      playingMessageId: identical(playingMessageId, _chatUnset)
          ? this.playingMessageId
          : playingMessageId as String?,
      isPlaying: isPlaying ?? this.isPlaying,
      searchMode: searchMode ?? this.searchMode,
      searchQuery: searchQuery ?? this.searchQuery,
      searchResults: searchResults ?? this.searchResults,
      searchCurrentIndex: searchCurrentIndex ?? this.searchCurrentIndex,
    );
  }
}
