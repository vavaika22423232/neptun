import 'package:flutter/material.dart';

class HolographicGrid extends StatefulWidget {
  final Widget? child;

  const HolographicGrid({super.key, this.child});

  @override
  State<HolographicGrid> createState() => _HolographicGridState();
}

class _HolographicGridState extends State<HolographicGrid>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 20),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        // Base dark gradient
        Container(
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [
                Color(0xFF0F172A), // Slate 900
                Color(0xFF020617), // Slate 950
              ],
            ),
          ),
        ),

        // Moving Grid
        AnimatedBuilder(
          animation: _controller,
          builder: (context, child) {
            return CustomPaint(
              painter: _GridPainter(_controller.value),
              child: Container(),
            );
          },
        ),

        // Content
        if (widget.child != null) widget.child!,
      ],
    );
  }
}

class _GridPainter extends CustomPainter {
  final double animationValue;

  _GridPainter(this.animationValue);

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = const Color(0xFF38BDF8)
          .withValues(alpha: 0.1) // Sky 400
      ..strokeWidth = 1.0;

    const spacing = 40.0;
    final offset = animationValue * spacing;

    // Vertical lines
    for (double x = 0; x < size.width; x += spacing) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), paint);
    }

    // Horizontal moving lines
    for (double y = offset - spacing; y < size.height; y += spacing) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), paint);
    }
  }

  @override
  bool shouldRepaint(_GridPainter oldDelegate) => true;
}
