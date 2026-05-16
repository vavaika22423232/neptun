/// Chat message data models for the native Flutter messenger.
class ChatMessage {
  final String id;
  final String userId;
  final String deviceId;
  final String message;
  final int timestamp;
  final String? time;
  final String? date;
  final bool isModerator;
  final bool isPro;
  final ReplyInfo? replyTo;
  final Map<String, List<ReactionInfo>> reactions;

  // Voice / image message fields
  final String messageType; // 'text', 'voice', 'image'
  final String? audioUrl;
  final int? audioDuration; // seconds
  final String? imageUrl;

  /// Unix timestamp (seconds) when message was last edited, null if never edited.
  final int? editedAt;

  ChatMessage({
    required this.id,
    required this.userId,
    required this.deviceId,
    required this.message,
    required this.timestamp,
    this.time,
    this.date,
    this.isModerator = false,
    this.isPro = false,
    this.replyTo,
    Map<String, List<ReactionInfo>>? reactions,
    this.messageType = 'text',
    this.audioUrl,
    this.audioDuration,
    this.imageUrl,
    this.editedAt,
  }) : reactions = reactions ?? {};

  bool get isEdited => editedAt != null;

  bool get isVoice => messageType == 'voice' && audioUrl != null;
  bool get isImage => messageType == 'image' && imageUrl != null;

  DateTime get dateTime => DateTime.fromMillisecondsSinceEpoch(timestamp);

  /// Total reaction count across all emojis.
  int get totalReactions =>
      reactions.values.fold(0, (sum, list) => sum + list.length);

  /// Check if this user has reacted with [emoji] (device id and/or nickname).
  bool hasReacted(String emoji, String deviceId, [String? myNickname]) {
    final list = reactions[emoji];
    if (list == null) return false;
    final nick = myNickname ?? '';
    return list.any(
      (r) => r.deviceId == deviceId || (nick.isNotEmpty && r.nickname == nick),
    );
  }

  /// The first letter of the nickname (for avatar).
  String get avatarLetter {
    if (userId.isNotEmpty) return userId[0].toUpperCase();
    return '?';
  }

  /// Two-letter initials for avatar (first two chars of nickname).
  String get avatarInitials {
    if (userId.length >= 2) {
      return userId.substring(0, 2).toUpperCase();
    }
    return avatarLetter;
  }

  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    // Parse reactions: { "👍": [{ deviceId, nickname, timestamp }], ... }
    final rawReactions = json['reactions'] as Map<String, dynamic>? ?? {};
    final parsedReactions = <String, List<ReactionInfo>>{};
    rawReactions.forEach((emoji, value) {
      if (value is List) {
        parsedReactions[emoji] = value
            .map((r) => ReactionInfo.fromJson(r as Map<String, dynamic>))
            .toList();
      }
    });

    // Parse replyTo
    ReplyInfo? replyInfo;
    final replyRaw = json['replyTo'];
    if (replyRaw != null && replyRaw is Map<String, dynamic>) {
      replyInfo = ReplyInfo.fromJson(replyRaw);
    } else if (replyRaw is String && replyRaw.isNotEmpty) {
      // Old format — just ID string
      replyInfo = ReplyInfo(id: replyRaw, nickname: null, text: null);
    }

    return ChatMessage(
      id: json['id']?.toString() ?? '',
      userId: json['userId']?.toString() ?? json['nickname']?.toString() ?? '',
      deviceId:
          json['deviceId']?.toString() ?? json['device_id']?.toString() ?? '',
      message: json['message']?.toString() ?? json['text']?.toString() ?? '',
      timestamp: _parseTimestamp(json['timestamp']),
      time: json['time']?.toString(),
      date: json['date']?.toString(),
      isModerator: json['isModerator'] == true,
      isPro: json['isPro'] == true,
      replyTo: replyInfo,
      reactions: parsedReactions,
      messageType:
          json['messageType']?.toString() ??
          json['message_type']?.toString() ??
          json['type']?.toString() ??
          'text',
      audioUrl: json['audioUrl']?.toString() ?? json['audio_url']?.toString(),
      audioDuration: _parseNullableInt(
        json['audioDuration'] ?? json['audio_duration'],
      ),
      imageUrl: json['imageUrl']?.toString() ?? json['image_url']?.toString(),
      editedAt: json['editedAt'] != null
          ? (json['editedAt'] is int
                ? json['editedAt'] as int
                : int.tryParse(json['editedAt'].toString()) ?? 0)
          : null,
    );
  }

  static int _parseTimestamp(dynamic value) {
    if (value is int) {
      // If it's a small integer (e.g. seconds since epoch), convert to ms
      if (value < 100000000000) return value * 1000;
      return value;
    }
    if (value is double) {
      // Seconds (e.g. 1771083623.91) -> ms
      return (value * 1000).toInt();
    }
    if (value is String) {
      final i = int.tryParse(value) ?? 0;
      if (i > 0 && i < 100000000000) return i * 1000;
      return i;
    }
    return 0;
  }

  static int? _parseNullableInt(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    if (value is String) return int.tryParse(value);
    return null;
  }

  ChatMessage copyWithReactions(Map<String, List<ReactionInfo>> newReactions) {
    return ChatMessage(
      id: id,
      userId: userId,
      deviceId: deviceId,
      message: message,
      timestamp: timestamp,
      time: time,
      date: date,
      isModerator: isModerator,
      isPro: isPro,
      replyTo: replyTo,
      reactions: newReactions,
      messageType: messageType,
      audioUrl: audioUrl,
      audioDuration: audioDuration,
      imageUrl: imageUrl,
      editedAt: editedAt,
    );
  }

  ChatMessage copyWithEdit({String? newMessage, int? newEditedAt}) {
    return ChatMessage(
      id: id,
      userId: userId,
      deviceId: deviceId,
      message: newMessage ?? message,
      timestamp: timestamp,
      time: time,
      date: date,
      isModerator: isModerator,
      isPro: isPro,
      replyTo: replyTo,
      reactions: reactions,
      messageType: messageType,
      audioUrl: audioUrl,
      audioDuration: audioDuration,
      imageUrl: imageUrl,
      editedAt: newEditedAt ?? editedAt,
    );
  }
}

class ReplyInfo {
  final String id;
  final String? nickname;
  final String? text;

  const ReplyInfo({required this.id, this.nickname, this.text});

  factory ReplyInfo.fromJson(Map<String, dynamic> json) {
    return ReplyInfo(
      id: json['id']?.toString() ?? '',
      nickname: json['nickname']?.toString(),
      text: json['text']?.toString() ?? json['message']?.toString(),
    );
  }
}

class ReactionInfo {
  final String deviceId;
  final String nickname;
  final int timestamp;

  const ReactionInfo({
    required this.deviceId,
    required this.nickname,
    required this.timestamp,
  });

  factory ReactionInfo.fromJson(Map<String, dynamic> json) {
    return ReactionInfo(
      deviceId: json['deviceId']?.toString() ?? '',
      nickname: json['nickname']?.toString() ?? '',
      timestamp: ChatMessage._parseTimestamp(json['timestamp']),
    );
  }
}
