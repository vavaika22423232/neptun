import 'package:flutter/material.dart';

import '../core/widgets/neptun_glass.dart';

/// Delegates to [NeptunGlass] for unified glass styling.
@Deprecated('Use NeptunGlass instead')
class GlassContainer extends StatelessWidget {
  final Widget child;
  final double blur;
  final double opacity;
  final EdgeInsetsGeometry padding;
  final EdgeInsetsGeometry margin;
  final double borderRadius;
  final Color? color;
  final Border? border;

  const GlassContainer({
    super.key,
    required this.child,
    this.blur = 15.0,
    this.opacity = 0.5,
    this.padding = const EdgeInsets.all(16.0),
    this.margin = EdgeInsets.zero,
    this.borderRadius = 24.0,
    this.color,
    this.border,
  });

  @override
  Widget build(BuildContext context) {
    return NeptunGlass(
      blur: blur,
      padding: padding,
      margin: margin,
      borderRadius: borderRadius,
      color: color?.withValues(alpha: opacity),
      border: border,
      child: child,
    );
  }
}
