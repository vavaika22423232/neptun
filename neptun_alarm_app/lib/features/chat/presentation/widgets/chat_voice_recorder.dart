import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../../theme/diary_design.dart';

/// Recording overlay with cancel, duration, and send buttons.
class ChatVoiceRecorder extends StatefulWidget {
  final int recordingSeconds;
  final VoidCallback onCancel;
  final VoidCallback onSend;
  final double dragOffset;

  const ChatVoiceRecorder({
    super.key,
    required this.recordingSeconds,
    required this.onCancel,
    required this.onSend,
    this.dragOffset = 0,
  });

  static String formatDuration(int seconds) {
    final m = seconds ~/ 60;
    final s = seconds % 60;
    return '$m:${s.toString().padLeft(2, '0')}';
  }

  @override
  State<ChatVoiceRecorder> createState() => _ChatVoiceRecorderState();
}

class _ChatVoiceRecorderState extends State<ChatVoiceRecorder> {
  bool _thresholdReached = false;

  @override
  void didUpdateWidget(ChatVoiceRecorder oldWidget) {
    super.didUpdateWidget(oldWidget);
    final reached = widget.dragOffset < -80;
    if (reached != _thresholdReached) {
      _thresholdReached = reached;
      if (reached) {
        HapticFeedback.selectionClick();
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final sendBg = isDark ? const Color(0xFF0EA5E9) : cs.primary;
    final sendFg = isDark ? DiaryColors.darkOnPrimary : cs.onPrimary;

    return Container(
      height: 64,
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      alignment: Alignment.center,
      color: Colors.transparent,
      child: Row(
        children: [
          _buildDeleteButton(cs),
          const SizedBox(width: 14),
          const _PulsingRecordDot(),
          const SizedBox(width: 10),
          Text(
            ChatVoiceRecorder.formatDuration(widget.recordingSeconds),
            style: GoogleFonts.plusJakartaSans(
              color: cs.onSurface,
              fontWeight: FontWeight.w800,
              fontSize: 17,
              letterSpacing: -0.5,
            ),
          ),
          const Spacer(),
          Flexible(
            child: _AnimatedSlideToCancel(dragOffset: widget.dragOffset),
          ),
          const SizedBox(width: 8),
          Tooltip(
            message: 'Надіслати голосове',
            child: IconButton.filled(
              onPressed: () {
                HapticFeedback.mediumImpact();
                widget.onSend();
              },
              style: IconButton.styleFrom(
                backgroundColor: sendBg,
                foregroundColor: sendFg,
              ),
              icon: const Icon(Icons.send_rounded, size: 22),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDeleteButton(ColorScheme cs) {
    final scale = (1.0 + (widget.dragOffset.abs() / 150)).clamp(1.0, 1.4);
    final glow = widget.dragOffset < -80;

    return Transform.scale(
      scale: scale,
      child: IconButton.filled(
        onPressed: () {
          HapticFeedback.mediumImpact();
          widget.onCancel();
        },
        style: IconButton.styleFrom(
          backgroundColor:
              glow ? cs.error : cs.errorContainer,
          foregroundColor: glow ? cs.onError : cs.onErrorContainer,
        ),
        icon: const Icon(Icons.delete_rounded, size: 22),
      ),
    );
  }
}

class _AnimatedSlideToCancel extends StatelessWidget {
  final double dragOffset;

  const _AnimatedSlideToCancel({required this.dragOffset});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    // Normalized opacity and offset
    final opacity = (1.0 - (dragOffset.abs() / 80)).clamp(0.0, 1.0);
    final offset = (dragOffset / 2).clamp(-40.0, 0.0);
    
    return Transform.translate(
      offset: Offset(offset, 0),
      child: Opacity(
        opacity: opacity,
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const _ChevronAnimation(),
            const SizedBox(width: 8),
            Flexible(
              child: Text(
                'Змахніть за скасування',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: GoogleFonts.plusJakartaSans(
                  fontSize: 14,
                  color: cs.onSurfaceVariant.withValues(alpha: 0.7),
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ChevronAnimation extends StatefulWidget {
  const _ChevronAnimation();

  @override
  State<_ChevronAnimation> createState() => _ChevronAnimationState();
}

class _ChevronAnimationState extends State<_ChevronAnimation>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        return Transform.translate(
          offset: Offset(-8 * _controller.value, 0),
          child: Opacity(
            opacity: 1.0 - _controller.value,
            child: Icon(Icons.keyboard_arrow_left_rounded, color: cs.onSurfaceVariant.withValues(alpha: 0.6), size: 24),
          ),
        );
      },
    );
  }
}

class _PulsingRecordDot extends StatefulWidget {
  const _PulsingRecordDot();

  @override
  State<_PulsingRecordDot> createState() => _PulsingRecordDotState();
}

class _PulsingRecordDotState extends State<_PulsingRecordDot>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 800),
      vsync: this,
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final errorColor = Theme.of(context).colorScheme.error;
    return AnimatedBuilder(
      animation: _controller,
      builder: (_, child) {
        return Container(
          width: 10,
          height: 10,
          decoration: BoxDecoration(
            color: errorColor.withValues(
              alpha: 0.5 + 0.5 * _controller.value,
            ),
            shape: BoxShape.circle,
            boxShadow: [
              BoxShadow(
                color: errorColor.withValues(
                  alpha: 0.3 * _controller.value,
                ),
                blurRadius: 6 * _controller.value,
                spreadRadius: 2 * _controller.value,
              ),
            ],
          ),
        );
      },
    );
  }
}
