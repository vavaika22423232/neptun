import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';

/// Recording overlay with cancel, duration, and send buttons.
class ChatVoiceRecorder extends StatelessWidget {
  final int recordingSeconds;
  final VoidCallback onCancel;
  final VoidCallback onSend;

  const ChatVoiceRecorder({
    super.key,
    required this.recordingSeconds,
    required this.onCancel,
    required this.onSend,
  });

  static String formatDuration(int seconds) {
    final m = seconds ~/ 60;
    final s = seconds % 60;
    return '$m:${s.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Container(
      decoration: BoxDecoration(
        color: cs.surfaceContainer,
        border: Border(top: BorderSide(color: cs.outline, width: 1)),
      ),
      child: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(8, 10, 8, 10),
          child: Row(
            children: [
              GestureDetector(
                onTap: () {
                  HapticFeedback.lightImpact();
                  onCancel();
                },
                child: Container(
                  width: 42,
                  height: 42,
                  decoration: BoxDecoration(
                    color: cs.error.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(21),
                  ),
                  child: Icon(Icons.delete_rounded, color: cs.error, size: 20),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const _PulsingRecordDot(),
                    const SizedBox(width: 8),
                    Text(
                      formatDuration(recordingSeconds),
                      style: GoogleFonts.inter(
                        color: cs.onSurface,
                        fontWeight: FontWeight.w600,
                        fontSize: 16,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              GestureDetector(
                onTap: () {
                  HapticFeedback.mediumImpact();
                  onSend();
                },
                child: Container(
                  width: 42,
                  height: 42,
                  decoration: BoxDecoration(
                    color: cs.primary,
                    borderRadius: BorderRadius.circular(21),
                  ),
                  child: const Icon(
                    Icons.send_rounded,
                    color: Colors.white,
                    size: 20,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
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
            color: errorColor.withValues(alpha: 0.5 + 0.5 * _controller.value),
            shape: BoxShape.circle,
            boxShadow: [
              BoxShadow(
                color: errorColor.withValues(alpha: 0.3 * _controller.value),
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
