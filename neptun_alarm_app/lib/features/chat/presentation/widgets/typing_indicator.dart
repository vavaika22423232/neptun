import 'dart:math' as math;
import 'dart:ui' show ImageFilter;

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Анімовані крапки «друкує» — хвиля з легким масштабом.
class ChatTypingIndicator extends StatefulWidget {
  const ChatTypingIndicator({super.key});

  @override
  State<ChatTypingIndicator> createState() => _ChatTypingIndicatorState();
}

class _ChatTypingIndicatorState extends State<ChatTypingIndicator>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 1400),
      vsync: this,
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
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return RepaintBoundary(
      child: AnimatedBuilder(
        animation: _controller,
        builder: (context, _) {
          return Row(
            mainAxisSize: MainAxisSize.min,
            children: List.generate(3, (i) {
              final phase = _controller.value * 2 * math.pi + i * 0.85;
              final wave = (math.sin(phase) + 1) * 0.5;
              final y = -4.2 * wave;
              final scale = 0.82 + 0.18 * wave;
              final glow = 0.35 + 0.55 * wave;

              final dotColor = Color.lerp(
                    cs.onSurfaceVariant.withValues(alpha: isDark ? 0.45 : 0.5),
                    cs.primary.withValues(alpha: 0.95),
                    glow,
                  ) ??
                  cs.primary;

              return Transform.translate(
                offset: Offset(0, y),
                child: Transform.scale(
                  scale: scale,
                  child: Container(
                    width: 7,
                    height: 7,
                    margin: const EdgeInsets.symmetric(horizontal: 2.5),
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: dotColor,
                      boxShadow: [
                        BoxShadow(
                          color: cs.primary.withValues(alpha: 0.22 * glow),
                          blurRadius: 4 + 3 * wave,
                          spreadRadius: 0.2,
                        ),
                      ],
                    ),
                  ),
                ),
              );
            }),
          );
        },
      ),
    );
  }
}

/// Плашка над полем вводу: ім’я + «пише / пишуть» у стилі чату.
class ChatTypingStatusBar extends StatelessWidget {
  const ChatTypingStatusBar({super.key, required this.users});

  final List<String> users;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final names = users.join(', ');
    final verb = users.length > 1 ? 'пишуть' : 'пише';

    return ClipRRect(
      borderRadius: BorderRadius.circular(24),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 18, sigmaY: 18),
        child: DecoratedBox(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(24),
            border: Border.all(
              color: cs.primary.withValues(alpha: isDark ? 0.28 : 0.2),
              width: 1,
            ),
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                cs.primary.withValues(alpha: isDark ? 0.14 : 0.1),
                cs.surfaceContainerHighest.withValues(
                  alpha: isDark ? 0.52 : 0.78,
                ),
                cs.surfaceContainer.withValues(alpha: isDark ? 0.38 : 0.65),
              ],
              stops: const [0.0, 0.45, 1.0],
            ),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: isDark ? 0.35 : 0.06),
                blurRadius: 20,
                offset: const Offset(0, 8),
              ),
              BoxShadow(
                color: cs.primary.withValues(alpha: 0.07),
                blurRadius: 24,
                spreadRadius: -4,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const ChatTypingIndicator(),
                const SizedBox(width: 8),
                Flexible(
                  child: Text.rich(
                    TextSpan(
                      children: [
                        TextSpan(
                          text: names,
                          style: GoogleFonts.plusJakartaSans(
                            fontSize: 12.5,
                            fontWeight: FontWeight.w600,
                            height: 1.2,
                            color: cs.onSurface.withValues(
                              alpha: isDark ? 0.9 : 0.85,
                            ),
                          ),
                        ),
                        TextSpan(
                          text: ' $verb…',
                          style: GoogleFonts.plusJakartaSans(
                            fontSize: 12,
                            fontWeight: FontWeight.w400,
                            height: 1.2,
                            color: cs.onSurfaceVariant.withValues(alpha: 0.7),
                          ),
                        ),
                      ],
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
