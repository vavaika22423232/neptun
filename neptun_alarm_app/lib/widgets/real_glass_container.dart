import 'package:flutter/material.dart';

import '../core/widgets/neptun_glass.dart';

/// Delegates to [NeptunGlass] for unified glass styling.
@Deprecated('Use NeptunGlass instead')
class RealGlassContainer extends StatelessWidget {
  final Widget child;
  final double? width;
  final double? height;
  final EdgeInsetsGeometry padding;
  final EdgeInsetsGeometry? margin;
  final double borderRadius;
  final double blurAmount;
  final Color? color;
  final Border? border;
  final VoidCallback? onTap;

  const RealGlassContainer({
    super.key,
    required this.child,
    this.width,
    this.height,
    this.padding = const EdgeInsets.all(16),
    this.margin,
    this.borderRadius = 24,
    this.blurAmount = 20,
    this.color,
    this.border,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: width,
      height: height,
      child: NeptunGlass(
        blur: blurAmount,
        padding: padding,
        margin: margin,
        borderRadius: borderRadius,
        color: color,
        border: border,
        onTap: onTap,
        child: child,
      ),
    );
  }
}
