import 'package:flutter/material.dart';

class GradientBackground extends StatefulWidget {
  final Widget? child;
  const GradientBackground({super.key, this.child});

  @override
  State<GradientBackground> createState() => _GradientBackgroundState();
}

class _GradientBackgroundState extends State<GradientBackground>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<Alignment> _topAlignmentAnimation;
  late Animation<Alignment> _bottomAlignmentAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 10),
    )..repeat(reverse: true);

    _topAlignmentAnimation = Tween<Alignment>(
      begin: Alignment.topLeft,
      end: Alignment.topRight,
    ).animate(_controller);

    _bottomAlignmentAnimation = Tween<Alignment>(
      begin: Alignment.bottomRight,
      end: Alignment.bottomLeft,
    ).animate(_controller);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        return Container(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: _topAlignmentAnimation.value,
              end: _bottomAlignmentAnimation.value,
              colors: isDark
                  ? [
                      const Color(0xFF0F0E17),
                      const Color(0xFF1B1B2F),
                      const Color(0xFF2E2E48),
                    ]
                  : [
                      const Color(0xFFF8F9FF), // Very light blue
                      const Color(0xFFE0E7FF), // Indigo tint
                      const Color(0xFFFCE7F3), // Subtle pink tint
                    ],
            ),
          ),
          child: widget.child,
        );
      },
    );
  }
}
