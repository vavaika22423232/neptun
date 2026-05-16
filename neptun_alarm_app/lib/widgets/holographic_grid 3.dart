import 'package:flutter/material.dart';

/// Тихий фон: базовий колір + статична сітка (без анімації).
class HolographicGrid extends StatelessWidget {
  final Widget? child;

  const HolographicGrid({super.key, this.child});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Stack(
      children: [
        ColoredBox(color: cs.surface),
        CustomPaint(
          painter: _StaticGridPainter(
            cs.primary.withValues(alpha: 0.06),
          ),
          child: const SizedBox.expand(),
        ),
        if (child case final Widget w) w,
      ],
    );
  }
}

class _StaticGridPainter extends CustomPainter {
  _StaticGridPainter(this.lineColor);

  final Color lineColor;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = lineColor
      ..strokeWidth = 1;

    const spacing = 40.0;
    for (double x = 0; x < size.width; x += spacing) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), paint);
    }
    for (double y = 0; y < size.height; y += spacing) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), paint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
