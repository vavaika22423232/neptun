import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../../../models/chat_message.dart';
import 'chat_voice_recorder.dart';

/// Input bar with text field, attachment button, reply preview, send/record.
class ChatInputBar extends StatelessWidget {
  final TextEditingController textController;
  final FocusNode focusNode;
  final ChatMessage? replyTo;
  final ChatMessage? editTo;
  final bool isSending;
  final bool isRecording;
  final int recordingSeconds;
  final VoidCallback onReplyDismiss;
  final VoidCallback? onEditDismiss;
  final void Function(bool) onTypingChanged;
  final VoidCallback onSend;
  final VoidCallback onStartRecording;
  final VoidCallback onCancelRecording;
  final VoidCallback onStopAndSendRecording;
  final VoidCallback? onAttach;

  const ChatInputBar({
    super.key,
    required this.textController,
    required this.focusNode,
    required this.replyTo,
    this.editTo,
    required this.isSending,
    required this.isRecording,
    required this.recordingSeconds,
    required this.onReplyDismiss,
    this.onEditDismiss,
    required this.onTypingChanged,
    required this.onSend,
    required this.onStartRecording,
    required this.onCancelRecording,
    required this.onStopAndSendRecording,
    this.onAttach,
  });

  @override
  Widget build(BuildContext context) {
    if (isRecording) {
      return ChatVoiceRecorder(
        recordingSeconds: recordingSeconds,
        onCancel: onCancelRecording,
        onSend: onStopAndSendRecording,
      );
    }

    final cs = Theme.of(context).colorScheme;
    return Container(
      decoration: BoxDecoration(
        color: cs.surfaceContainer,
        border: Border(top: BorderSide(color: cs.outline, width: 1)),
      ),
      child: SafeArea(
        top: false,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (editTo != null) _buildEditPreview(context),
            if (replyTo != null && editTo == null) _buildReplyPreview(context),
            Padding(
              padding: const EdgeInsets.fromLTRB(8, 6, 8, 6),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  if (onAttach != null)
                    GestureDetector(
                      onTap: () {
                        HapticFeedback.lightImpact();
                        onAttach!();
                      },
                      child: Container(
                        width: 42,
                        height: 42,
                        margin: const EdgeInsets.only(right: 4),
                        decoration: BoxDecoration(
                          color: cs.onSurface.withValues(alpha: 0.1),
                          borderRadius: BorderRadius.circular(21),
                        ),
                        child: Icon(
                          Icons.add_rounded,
                          color: cs.onSurface.withValues(alpha: 0.6),
                          size: 24,
                        ),
                      ),
                    ),
                  Expanded(
                    child: TextField(
                      controller: textController,
                      focusNode: focusNode,
                      maxLines: 4,
                      minLines: 1,
                      maxLength: 500,
                      style: GoogleFonts.inter(
                        color: cs.onSurface,
                        fontSize: 15,
                      ),
                      decoration: InputDecoration(
                        hintText: 'Повідомлення...',
                        hintStyle: GoogleFonts.inter(
                          color: cs.onSurface.withValues(alpha: 0.35),
                          fontSize: 15,
                        ),
                        counterText: '',
                        filled: true,
                        fillColor: cs.surfaceContainerHighest,
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(24),
                          borderSide: BorderSide.none,
                        ),
                        contentPadding: const EdgeInsets.symmetric(
                          horizontal: 18,
                          vertical: 10,
                        ),
                      ),
                      onChanged: (val) =>
                          onTypingChanged(val.trim().isNotEmpty),
                      onSubmitted: (_) => onSend(),
                      textInputAction: TextInputAction.send,
                    ),
                  ),
                  const SizedBox(width: 6),
                  ValueListenableBuilder<TextEditingValue>(
                    valueListenable: textController,
                    builder: (_, value, child) {
                      final hasText = value.text.trim().isNotEmpty;
                      return GestureDetector(
                        onTap: isSending
                            ? null
                            : hasText
                                ? onSend
                                : onStartRecording,
                        onLongPressStart: hasText || isSending
                            ? null
                            : (_) => onStartRecording(),
                        onLongPressEnd: hasText || isSending
                            ? null
                            : (_) => onStopAndSendRecording(),
                        child: AnimatedContainer(
                          duration: const Duration(milliseconds: 200),
                          width: 42,
                          height: 42,
                          decoration: BoxDecoration(
                            color: hasText || isSending
                                ? cs.primary
                                : cs.onSurface.withValues(alpha: 0.15),
                            borderRadius: BorderRadius.circular(21),
                          ),
                          child: isSending
                              ? const Padding(
                                  padding: EdgeInsets.all(10),
                                  child: CircularProgressIndicator(
                                    color: Colors.white,
                                    strokeWidth: 2,
                                  ),
                                )
                              : AnimatedSwitcher(
                                  duration: const Duration(milliseconds: 200),
                                  child: Icon(
                                    hasText
                                        ? Icons.send_rounded
                                        : Icons.mic_rounded,
                                    key: ValueKey(hasText),
                                    color: hasText
                                        ? Colors.white
                                        : cs.onSurface.withValues(alpha: 0.5),
                                    size: 20,
                                  ),
                                ),
                        ),
                      );
                    },
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEditPreview(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    if (editTo == null || onEditDismiss == null) return const SizedBox.shrink();
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 8, 8, 4),
      decoration: BoxDecoration(
        border: Border(bottom: BorderSide(color: cs.outline, width: 0.5)),
      ),
      child: Row(
        children: [
          Container(
            width: 3,
            height: 32,
            decoration: BoxDecoration(
              color: cs.tertiary,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  'Редагування',
                  style: GoogleFonts.inter(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: cs.tertiary,
                  ),
                ),
                Text(
                  editTo!.message,
                  style: GoogleFonts.inter(
                    fontSize: 12,
                    color: cs.onSurfaceVariant,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
          IconButton(
            icon: Icon(
              Icons.close_rounded,
              size: 18,
              color: cs.onSurface.withValues(alpha: 0.35),
            ),
            onPressed: onEditDismiss,
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
          ),
        ],
      ),
    );
  }

  Widget _buildReplyPreview(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 8, 8, 4),
      decoration: BoxDecoration(
        border: Border(bottom: BorderSide(color: cs.outline, width: 0.5)),
      ),
      child: Row(
        children: [
          Container(
            width: 3,
            height: 32,
            decoration: BoxDecoration(
              color: cs.primary,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  replyTo!.userId,
                  style: GoogleFonts.inter(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: cs.primary,
                  ),
                ),
                Text(
                  replyTo!.message,
                  style: GoogleFonts.inter(
                    fontSize: 12,
                    color: cs.onSurfaceVariant,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
          IconButton(
            icon: Icon(
              Icons.close_rounded,
              size: 18,
              color: cs.onSurface.withValues(alpha: 0.35),
            ),
            onPressed: onReplyDismiss,
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
          ),
        ],
      ),
    );
  }
}
