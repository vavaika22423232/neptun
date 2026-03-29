import 'package:flutter/material.dart';
import 'dart:math' as math;
/// Soft animated gradient background for modern glassmorphism aesthetic
class AmbientBackground extends StatefulWidget {
  const AmbientBackground({super.key});

  @override
  State<AmbientBackground> createState() => _AmbientBackgroundState();
}

class _AmbientBackgroundState extends State<AmbientBackground>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(seconds: 15), // Slightly faster for flow
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
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        return CustomPaint(
          painter: _PastelBlobPainter(
            animation: _controller.value,
            isDark: isDark,
          ),
          child: Container(),
        );
      },
    );
  }
}

class _PastelBlobPainter extends CustomPainter {
  final double animation;
  final bool isDark;

  _PastelBlobPainter({required this.animation, required this.isDark});

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..style = PaintingStyle.fill;

    // Soft ambient gradients — cyan-teal accent (Design 4.0)
    if (isDark) {
      _drawBlob(
        canvas,
        size,
        paint,
        [
          const Color(0xFF0891B2).withValues(alpha: 0.12),
          const Color(0xFF22D3EE).withValues(alpha: 0.04),
        ],
        Offset(
          size.width * 0.2 + math.sin(animation * 2 * math.pi) * 30,
          size.height * 0.3 + math.cos(animation * 2 * math.pi) * 30,
        ),
        size.width * 0.6,
      );

      _drawBlob(
        canvas,
        size,
        paint,
        [
          const Color(0xFF0E7490).withValues(alpha: 0.08),
          const Color(0xFF155E75).withValues(alpha: 0.03),
        ],
        Offset(
          size.width * 0.8 + math.cos(animation * 2 * math.pi * 0.8) * 40,
          size.height * 0.7 + math.sin(animation * 2 * math.pi * 0.8) * 40,
        ),
        size.width * 0.7,
      );
    } else {
      _drawBlob(
        canvas,
        size,
        paint,
        [
          const Color(0xFF06B6D4).withValues(alpha: 0.12),
          Colors.white.withValues(alpha: 0.0),
        ],
        Offset(
          size.width * 0.2 + math.sin(animation * 2 * math.pi) * 60,
          size.height * 0.3 + math.cos(animation * 2 * math.pi) * 40,
        ),
        size.width * 0.7,
      );

      _drawBlob(
        canvas,
        size,
        paint,
        [
          const Color(0xFF22D3EE).withValues(alpha: 0.08),
          Colors.white.withValues(alpha: 0.0),
        ],
        Offset(
          size.width * 0.8 - math.sin(animation * 2 * math.pi * 0.7) * 50,
          size.height * 0.7 - math.cos(animation * 2 * math.pi * 0.7) * 50,
        ),
        size.width * 0.8,
      );

      _drawBlob(
        canvas,
        size,
        paint,
        [
          const Color(0xFF34D399).withValues(alpha: 0.06),
          Colors.white.withValues(alpha: 0.0),
        ],
        Offset(
          size.width * 0.5 + math.cos(animation * 2 * math.pi * 1.2) * 80,
          size.height * 0.5 + math.sin(animation * 2 * math.pi * 1.2) * 80,
        ),
        size.width * 0.5,
      );
    }
  }

  void _drawBlob(
    Canvas canvas,
    Size size,
    Paint paint,
    List<Color> colors,
    Offset center,
    double radius,
  ) {
    paint.shader = RadialGradient(
      colors: colors,
      stops: const [0.0, 1.0],
    ).createShader(Rect.fromCircle(center: center, radius: radius));

    canvas.drawCircle(center, radius, paint);
  }

  @override
  bool shouldRepaint(_PastelBlobPainter oldDelegate) {
    return oldDelegate.animation != animation || oldDelegate.isDark != isDark;
  }
}
