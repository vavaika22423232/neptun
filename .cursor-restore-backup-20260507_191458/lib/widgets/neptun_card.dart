import 'package:flutter/material.dart';

import '../design/neptun_design.dart';

/// Simple card component: solid fill + border + radius.
class NeptunCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry? padding;
  final EdgeInsetsGeometry? margin;
  final double? borderRadius;
  final Color? backgroundColor;
  final Color? borderColor;
  final VoidCallback? onTap;
  final VoidCallback? onLongPress;

  const NeptunCard({
    super.key,
    required this.child,
    this.padding,
    this.margin,
    this.borderRadius,
    this.backgroundColor,
    this.borderColor,
    this.onTap,
    this.onLongPress,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final cs = Theme.of(context).colorScheme;

    final radius = borderRadius ?? NeptunRadius.lg;
    final bg =
        backgroundColor ?? (isDark ? NeptunSurfaces.s1 : cs.surfaceContainer);
    final border =
        borderColor ??
        (isDark
            ? NeptunSurfaces.border.withValues(alpha: 0.6)
            : cs.outline.withValues(alpha: 0.12));

    Widget content = Padding(
      padding: padding ?? NeptunSpacing.cardPadding,
      child: child,
    );

    if (onTap != null || onLongPress != null) {
      content = InkWell(
        onTap: onTap,
        onLongPress: onLongPress,
        borderRadius: BorderRadius.circular(radius),
        child: content,
      );
    }

    return Container(
      margin: margin,
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(radius),
        border: Border.all(color: border, width: 0.5),
      ),
      child: Material(color: Colors.transparent, child: content),
    );
  }
}
