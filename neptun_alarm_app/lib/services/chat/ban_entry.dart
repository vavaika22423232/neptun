/// Ban entry with reason and metadata (chat API / admin list).
class BanEntry {
  final String nickname;
  final String deviceId;
  final String? hardwareId;
  final String reason;
  final String? bannedAt;
  final String? bannedBy;

  const BanEntry({
    required this.nickname,
    this.deviceId = '',
    this.hardwareId,
    required this.reason,
    this.bannedAt,
    this.bannedBy,
  });

  String get stableKey {
    final hw = hardwareId?.trim() ?? '';
    if (deviceId.trim().isNotEmpty) return 'device:$deviceId';
    if (hw.isNotEmpty) return 'hardware:$hw';
    return 'nick:${nickname.toLowerCase()}';
  }
}

BanEntry banEntryFromJson(Map<String, dynamic> j) {
  return BanEntry(
    nickname: j['nickname']?.toString() ?? '',
    deviceId: j['device_id']?.toString() ?? '',
    hardwareId: j['hardware_id']?.toString(),
    reason: j['reason']?.toString() ?? 'Порушення правил',
    bannedAt: j['banned_at']?.toString(),
    bannedBy: j['banned_by']?.toString(),
  );
}
