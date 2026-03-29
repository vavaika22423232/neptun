import 'package:flutter/material.dart';

/// Shimmer loading placeholder for the design system.
/// Replaces legacy ShimmerLoading with Theme-aware colors.
class NeptunShimmer extends StatefulWidget {
  final double width;
  final double height;
  final double borderRadius;

  const NeptunShimmer({
    super.key,
    this.width = double.infinity,
    this.height = 20,
    this.borderRadius = 8,
  });

  @override
  State<NeptunShimmer> createState() => _NeptunShimmerState();
}

class _NeptunShimmerState extends State<NeptunShimmer>
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
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final baseColor = isDark
        ? cs.surfaceContainerHighest.withValues(alpha: 0.6)
        : cs.surfaceContainerHighest;
    final highlightColor = isDark
        ? cs.surfaceContainerHighest
        : cs.surfaceContainerHighest.withValues(alpha: 0.9);

    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        return Container(
          width: widget.width,
          height: widget.height,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(widget.borderRadius),
            gradient: LinearGradient(
              begin: Alignment(-1.0 + 2.0 * _controller.value, 0),
              end: Alignment(1.0 + 2.0 * _controller.value, 0),
              colors: [baseColor, highlightColor, baseColor],
              stops: const [0.0, 0.5, 1.0],
            ),
          ),
        );
      },
    );
  }
}
