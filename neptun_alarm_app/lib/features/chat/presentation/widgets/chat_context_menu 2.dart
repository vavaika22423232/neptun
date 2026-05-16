import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../../../models/chat_message.dart';

/// Telegram-style context menu overlay for message actions.
class ChatContextMenuOverlay extends StatelessWidget {
  final ChatMessage message;
  final bool isMine;
  final bool isModerator;
  final String myDeviceId;
  final void Function(String emoji) onReact;
  final VoidCallback onReply;
  final VoidCallback onCopy;
  final VoidCallback onDelete;
  final VoidCallback? onBan;
  final VoidCallback? onReport;
  final VoidCallback? onBlock;
  final VoidCallback? onEdit;
  final VoidCallback? onDeleteAll;

  const ChatContextMenuOverlay({
    super.key,
    required this.message,
    required this.isMine,
    required this.isModerator,
    required this.myDeviceId,
    required this.onReact,
    required this.onReply,
    required this.onCopy,
    required this.onDelete,
    this.onBan,
    this.onReport,
    this.onBlock,
    this.onEdit,
    this.onDeleteAll,
  });

  static const _emojis = ['👍', '❤️', '😂', '😮', '😢', '🔥', '🇺🇦'];

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return GestureDetector(
      onTap: () => Navigator.pop(context),
      child: Container(
        color: Colors.black.withValues(alpha: 0.5),
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                margin: const EdgeInsets.symmetric(horizontal: 32),
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                decoration: BoxDecoration(
                  color: cs.surfaceContainerHighest,
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: cs.outline),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: _emojis.map((emoji) {
                    final hasReacted = message.hasReacted(emoji, myDeviceId);
                    return GestureDetector(
                      onTap: () => onReact(emoji),
                      child: Container(
                        margin: const EdgeInsets.symmetric(horizontal: 2),
                        padding: const EdgeInsets.all(6),
                        decoration: BoxDecoration(
                          color: hasReacted
                              ? cs.primary.withValues(alpha: 0.15)
                              : Colors.transparent,
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Text(
                          emoji,
                          style: const TextStyle(fontSize: 24),
                        ),
                      ),
                    );
                  }).toList(),
                ),
              ),
              const SizedBox(height: 8),
              Container(
                margin: const EdgeInsets.symmetric(horizontal: 48),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: isMine
                      ? cs.primary.withValues(alpha: 0.15)
                      : cs.surfaceContainerHighest,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: cs.outline, width: 0.5),
                ),
                child: Text(
                  message.message,
                  style: GoogleFonts.inter(fontSize: 14, color: cs.onSurface),
                  maxLines: 4,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              const SizedBox(height: 8),
              Material(
                color: Colors.transparent,
                child: Container(
                  margin: const EdgeInsets.symmetric(horizontal: 32),
                  decoration: BoxDecoration(
                    color: cs.surfaceContainerHighest,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: cs.outline),
                  ),
                  child: Column(
                    children: [
                      _actionTile(context, Icons.reply_rounded, 'Відповісти', onReply),
                      _divider(context),
                      _actionTile(context, Icons.copy_rounded, 'Копіювати', onCopy),
                      if (isMine && !message.isVoice && onEdit != null) ...[
                        _divider(context),
                        _actionTile(
                          context,
                          Icons.edit_rounded,
                          'Редагувати',
                          onEdit!,
                        ),
                      ],
                      if (isMine || isModerator) ...[
                        _divider(context),
                        _actionTile(
                          context,
                          Icons.delete_outline_rounded,
                          'Видалити',
                          onDelete,
                          color: cs.error,
                        ),
                      ],
                      if (onBan != null && !isMine) ...[
                        _divider(context),
                        _actionTile(
                          context,
                          Icons.block_rounded,
                          'Заблокувати (модератор)',
                          onBan!,
                          color: cs.error,
                        ),
                      ],
                      if (onDeleteAll != null && !isMine) ...[
                        _divider(context),
                        _actionTile(
                          context,
                          Icons.delete_sweep_rounded,
                          'Видалити всі повідомлення',
                          onDeleteAll!,
                          color: cs.error,
                        ),
                      ],
                      if (!isMine && onReport != null) ...[
                        _divider(context),
                        _actionTile(
                          context,
                          Icons.flag_rounded,
                          'Поскаржитись',
                          onReport!,
                          color: cs.tertiary,
                        ),
                      ],
                      if (!isMine && onBlock != null) ...[
                        _divider(context),
                        _actionTile(
                          context,
                          Icons.person_off_rounded,
                          'Сховати користувача',
                          onBlock!,
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _actionTile(
    BuildContext context,
    IconData icon,
    String label,
    VoidCallback onTap, {
    Color? color,
  }) {
    final cs = Theme.of(context).colorScheme;
    final c = color ?? cs.onSurface;
    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 13),
        child: Row(
          children: [
            Icon(icon, size: 20, color: c),
            const SizedBox(width: 12),
            Text(label, style: GoogleFonts.inter(fontSize: 15, color: c)),
          ],
        ),
      ),
    );
  }

  Widget _divider(BuildContext context) {
    return Divider(
      height: 0.5,
      thickness: 0.5,
      color: Theme.of(context).colorScheme.outline,
    );
  }
}
