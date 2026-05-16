import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../../models/chat_message.dart';
import '../../../../services/chat_service.dart';
import '../../../../theme/diary_design.dart';
import 'chat_voice_recorder.dart';

/// Панель введення чату — Material 3 (surface containers, FilledButton / tonal).
class ChatInputBar extends StatefulWidget {
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
  State<ChatInputBar> createState() => _ChatInputBarState();
}

class _ChatInputBarState extends State<ChatInputBar> {
  static const double _outerRadius = 28;
  static const double _actionSize = 48;
  static const double _fieldRadius = 24;

  double _recordingDragX = 0;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return GestureDetector(
      onPanUpdate: widget.isRecording
          ? (details) {
              setState(() => _recordingDragX += details.delta.dx);
              if (_recordingDragX < -100) {
                widget.onCancelRecording();
                setState(() => _recordingDragX = 0);
              }
            }
          : null,
      onPanEnd: widget.isRecording
          ? (_) {
              setState(() => _recordingDragX = 0);
            }
          : null,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 6, 12, 8),
        child: _buildBarShell(
          context,
          AnimatedSwitcher(
            duration: const Duration(milliseconds: 300),
            transitionBuilder: (child, anim) =>
                FadeTransition(opacity: anim, child: child),
            child: widget.isRecording
                ? ChatVoiceRecorder(
                    key: const ValueKey('recorder'),
                    recordingSeconds: widget.recordingSeconds,
                    onCancel: widget.onCancelRecording,
                    onSend: widget.onStopAndSendRecording,
                    dragOffset: _recordingDragX,
                  )
                : Column(
                    key: const ValueKey('input'),
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      AnimatedSize(
                        duration: const Duration(milliseconds: 300),
                        curve: Curves.easeOutCubic,
                        child: AnimatedSwitcher(
                          duration: const Duration(milliseconds: 250),
                          transitionBuilder: (child, animation) {
                            return FadeTransition(
                              opacity: animation,
                              child: SizeTransition(
                                sizeFactor: animation,
                                child: child,
                              ),
                            );
                          },
                          child: widget.editTo != null
                              ? RepaintBoundary(
                                  child: _buildActionPreview(
                                    context,
                                    isEdit: true,
                                    key: const ValueKey('edit'),
                                  ),
                                )
                              : (widget.replyTo != null
                                    ? RepaintBoundary(
                                        child: _buildActionPreview(
                                          context,
                                          isEdit: false,
                                          key: const ValueKey('reply'),
                                        ),
                                      )
                                    : const SizedBox.shrink(
                                        key: ValueKey('none'),
                                      )),
                        ),
                      ),
                      Padding(
                        padding: const EdgeInsets.fromLTRB(10, 10, 10, 10),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            _buildOrbAttachButton(cs),
                            const SizedBox(width: 10),
                            Expanded(child: _buildInsetTextField(cs)),
                            const SizedBox(width: 10),
                            RepaintBoundary(child: _buildOrbActionButton(cs)),
                          ],
                        ),
                      ),
                    ],
                  ),
          ),
        ),
      ),
    );
  }

  /// Зовнішня «пігулка» — M3 [surfaceContainerHigh], outlineVariant, легкий elevation.
  Widget _buildBarShell(BuildContext context, Widget child) {
    final cs = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Material(
      elevation: isDark ? 3 : 1,
      shadowColor: Colors.black.withValues(alpha: isDark ? 0.4 : 0.12),
      surfaceTintColor: Colors.transparent,
      // Одна «плита» з лентою повідомлень, не зливається з фоном
      color: isDark ? cs.surfaceContainerHigh : Theme.of(context).scaffoldBackgroundColor,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(_outerRadius),
        side: BorderSide(
          color: cs.outlineVariant.withValues(alpha: isDark ? 0.5 : 0.55),
          width: 1,
        ),
      ),
      clipBehavior: Clip.antiAlias,
      child: child,
    );
  }

  Widget _buildOrbAttachButton(ColorScheme cs) {
    return IconButton(
      onPressed: widget.onAttach == null
          ? null
          : () {
              HapticFeedback.lightImpact();
              widget.onAttach!();
            },
      style: IconButton.styleFrom(
        backgroundColor: cs.surfaceContainerLow,
        foregroundColor: cs.onSurfaceVariant,
        shape: const CircleBorder(),
        padding: EdgeInsets.zero,
        minimumSize: const Size(_actionSize, _actionSize),
        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
        visualDensity: VisualDensity.standard,
      ),
      tooltip: 'Фото або файл',
      icon: const Icon(Icons.add_rounded, size: 24),
    );
  }

  /// Поле введення — M3 [surfaceContainerLow] + primary border у фокусі.
  Widget _buildInsetTextField(ColorScheme cs) {
    return ListenableBuilder(
      listenable: widget.focusNode,
      builder: (context, _) {
        final focused = widget.focusNode.hasFocus;
        final isDark = Theme.of(context).brightness == Brightness.dark;
        final borderSide = BorderSide(
          color: focused
              ? (isDark
                  ? const Color(0xFF38BDF8)
                  : cs.primary)
              : cs.outlineVariant.withValues(alpha: isDark ? 0.5 : 0.55),
          width: focused ? 2 : 1,
        );
        return AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeOutCubic,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(_fieldRadius),
            color: isDark
                ? DiaryColors.darkSurfaceElevated.withValues(alpha: 0.85)
                : cs.surfaceContainerLow,
            border: Border.fromBorderSide(borderSide),
          ),
          clipBehavior: Clip.antiAlias,
          child: TextField(
            controller: widget.textController,
            focusNode: widget.focusNode,
            maxLines: 5,
            minLines: 1,
            maxLength: ChatService.maxMessageLength,
            cursorColor: isDark ? const Color(0xFF38BDF8) : cs.primary,
            style: GoogleFonts.plusJakartaSans(
              fontSize: 15,
              height: 1.4,
              color: cs.onSurface,
              fontWeight: FontWeight.w500,
            ),
            decoration: InputDecoration(
              hintText: 'Напишіть повідомлення…',
              hintStyle: GoogleFonts.plusJakartaSans(
                color: cs.onSurfaceVariant.withValues(alpha: 0.72),
                fontWeight: FontWeight.w500,
                fontSize: 15,
              ),
              filled: false,
              isCollapsed: false,
              isDense: true,
              contentPadding: const EdgeInsets.fromLTRB(16, 14, 14, 14),
              counterText: '',
              border: InputBorder.none,
              enabledBorder: InputBorder.none,
              focusedBorder: InputBorder.none,
              disabledBorder: InputBorder.none,
              errorBorder: InputBorder.none,
              focusedErrorBorder: InputBorder.none,
            ),
            onChanged: (val) => widget.onTypingChanged(val.trim().isNotEmpty),
          ),
        );
      },
    );
  }

  Widget _buildOrbActionButton(ColorScheme cs) {
    return ValueListenableBuilder<TextEditingValue>(
      valueListenable: widget.textController,
      builder: (context, value, _) {
        final hasText = value.text.trim().isNotEmpty;
        final isSend = hasText;
        final isDark = Theme.of(context).brightness == Brightness.dark;

        void onTap() {
          if (widget.isSending) return;
          if (hasText) {
            HapticFeedback.mediumImpact();
            widget.onSend();
          } else {
            HapticFeedback.mediumImpact();
            widget.onStartRecording();
          }
        }

        /// Тёмная тема: не «белый диск», а sky — узнаваемый акцент Neptun.
        final sendBg =
            isDark ? const Color(0xFF0EA5E9) : cs.primary;
        final sendFg =
            isDark ? DiaryColors.darkOnPrimary : cs.onPrimary;

        final buttonStyle = FilledButton.styleFrom(
          shape: const CircleBorder(),
          padding: EdgeInsets.zero,
          minimumSize: const Size(_actionSize, _actionSize),
          maximumSize: const Size(_actionSize, _actionSize),
          tapTargetSize: MaterialTapTargetSize.shrinkWrap,
          visualDensity: VisualDensity.standard,
          backgroundColor: sendBg,
          foregroundColor: sendFg,
          disabledBackgroundColor: sendBg.withValues(alpha: 0.45),
          disabledForegroundColor: sendFg.withValues(alpha: 0.6),
        );

        final actionChild = AnimatedSwitcher(
          duration: const Duration(milliseconds: 220),
          transitionBuilder: (child, anim) =>
              ScaleTransition(scale: anim, child: child),
          child: Center(
            key: ValueKey('${hasText}_${widget.isSending}'),
            child: widget.isSending
                ? SizedBox(
                    width: 22,
                    height: 22,
                    child: CircularProgressIndicator(
                      strokeWidth: 2.2,
                      color: sendFg,
                    ),
                  )
                : Icon(
                    Icons.send_rounded,
                    color: sendFg,
                    size: 22,
                  ),
          ),
        );

        if (isSend || widget.isSending) {
          return Tooltip(
            message: 'Надіслати',
            child: FilledButton(
              onPressed: widget.isSending ? null : onTap,
              style: buttonStyle,
              child: actionChild,
            ),
          );
        }

        // Не FilledButton.tonal — у темній темі tonal інколи дає «білий диск» і майже той самий
        // колір іконки (onSecondaryContainer), мікрофон зникає. Ті самі кольори, що кнопка «+».
        return Tooltip(
          message: 'Утримуйте для запису',
          child: GestureDetector(
            behavior: HitTestBehavior.opaque,
            onLongPressStart: widget.isSending
                ? null
                : (_) {
                    HapticFeedback.mediumImpact();
                    widget.onStartRecording();
                  },
            onLongPressEnd: widget.isSending
                ? null
                : (_) => widget.onStopAndSendRecording(),
            child: IconButton(
              onPressed: widget.isSending ? null : onTap,
              style: IconButton.styleFrom(
                backgroundColor: cs.surfaceContainerLow,
                foregroundColor: cs.onSurfaceVariant,
                disabledBackgroundColor:
                    cs.surfaceContainerLow.withValues(alpha: 0.45),
                disabledForegroundColor:
                    cs.onSurfaceVariant.withValues(alpha: 0.38),
                shape: const CircleBorder(),
                padding: EdgeInsets.zero,
                minimumSize: const Size(_actionSize, _actionSize),
                tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                visualDensity: VisualDensity.standard,
              ),
              icon: const Icon(Icons.mic_none_rounded, size: 22),
            ),
          ),
        );
      },
    );
  }

  Widget _buildActionPreview(
    BuildContext context, {
    required bool isEdit,
    Key? key,
  }) {
    final cs = Theme.of(context).colorScheme;
    final message = isEdit ? widget.editTo! : widget.replyTo!;
    final title = isEdit ? 'Редагування' : message.userId;
    final icon = isEdit ? Icons.edit_rounded : Icons.reply_rounded;
    final accentColor = cs.onSurface;

    return Container(
      key: key,
      padding: const EdgeInsets.fromLTRB(12, 10, 6, 10),
      decoration: BoxDecoration(
        color: cs.surfaceContainerLow,
        border: Border(
          bottom: BorderSide(color: cs.outlineVariant.withValues(alpha: 0.5)),
        ),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(6),
            decoration: BoxDecoration(
              color: accentColor.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(icon, color: accentColor, size: 16),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  title,
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 10,
                    fontWeight: FontWeight.w800,
                    color: accentColor,
                    letterSpacing: 0.3,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  message.message,
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 12,
                    color: cs.onSurfaceVariant.withValues(alpha: 0.78),
                    fontWeight: FontWeight.w500,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
          IconButton(
            onPressed: () {
              HapticFeedback.lightImpact();
              isEdit
                  ? widget.onEditDismiss?.call()
                  : widget.onReplyDismiss.call();
            },
            style: IconButton.styleFrom(
              padding: EdgeInsets.zero,
              minimumSize: const Size(28, 28),
              tapTargetSize: MaterialTapTargetSize.shrinkWrap,
              visualDensity: VisualDensity.compact,
            ),
            icon: Icon(
              Icons.close_rounded,
              size: 18,
              color: cs.onSurfaceVariant.withValues(alpha: 0.55),
            ),
          ),
        ],
      ),
    );
  }
}
