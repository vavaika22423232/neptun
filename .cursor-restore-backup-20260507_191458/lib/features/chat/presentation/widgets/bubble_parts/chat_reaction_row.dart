import 'package:flutter/material.dart';
import '../../../../../models/chat_message.dart';

class ChatReactionRow extends StatelessWidget {
  final Map<String, List<ReactionInfo>> reactions;
  final String myDeviceId;
  final String? myNickname;
  final void Function(String emoji) onReact;
  final ColorScheme colorScheme;

  const ChatReactionRow({
    super.key,
    required this.reactions,
    required this.myDeviceId,
    this.myNickname,
    required this.onReact,
    required this.colorScheme,
  });

  @override
  Widget build(BuildContext context) {
    if (reactions.isEmpty) return const SizedBox.shrink();

    return Padding(
      padding: const EdgeInsets.fromLTRB(8, 0, 8, 8),
      child: Wrap(
        spacing: 4,
        runSpacing: 4,
        children: reactions.entries.map((e) {
          final isMine = _hasReacted(e.value, myDeviceId, myNickname);
          return Semantics(
            label: 'Реакція ${e.key}, кількість ${e.value.length}',
            button: true,
            child: GestureDetector(
              onTap: () => onReact(e.key),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: isMine
                      ? colorScheme.primary.withValues(alpha: 0.15)
                      : colorScheme.surfaceContainerLow,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: isMine
                        ? colorScheme.primary.withValues(alpha: 0.3)
                        : colorScheme.outlineVariant,
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(e.key, style: const TextStyle(fontSize: 13)),
                    if (e.value.length > 1) ...[
                      const SizedBox(width: 4),
                      Text(
                        '${e.value.length}',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                          color: isMine
                              ? colorScheme.primary
                              : colorScheme.onSurface.withValues(alpha: 0.6),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          );
        }).toList(),
      ),
    );
  }

  bool _hasReacted(
    List<ReactionInfo> infos,
    String deviceId,
    String? myNickname,
  ) {
    return infos.any((r) {
      if (deviceId.isNotEmpty && r.deviceId == deviceId) return true;
      if (myNickname != null &&
          myNickname.isNotEmpty &&
          r.nickname == myNickname) {
        return true;
      }
      return false;
    });
  }
}
