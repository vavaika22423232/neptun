import 'package:flutter/material.dart';

import '../neptun_design.dart';

/// Уніфікована плитка bento: поверхня з теми, радіус [NeptunSpacing.bentoRadius].
class NeptunBentoSurface extends StatelessWidget {
  const NeptunBentoSurface({
    super.key,
    required this.child,
    this.padding,
    this.margin,
    this.onTap,
    this.radius,
    this.showBorder = true,
  });

  final Widget child;
  final EdgeInsetsGeometry? padding;
  final EdgeInsetsGeometry? margin;
  final VoidCallback? onTap;
  final double? radius;
  final bool showBorder;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final r = radius ?? NeptunSpacing.bentoRadius;
    final bg = isDark ? cs.surfaceContainer : cs.surfaceContainerHighest;
    final borderColor = cs.outline.withValues(alpha: isDark ? 0.22 : 0.12);

    Widget inner = Padding(
      padding: padding ?? const EdgeInsets.all(NeptunSpacing.lg),
      child: child,
    );

    if (onTap != null) {
      inner = Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(r),
          child: inner,
        ),
      );
    }

    return Padding(
      padding: margin ?? EdgeInsets.zero,
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: bg,
          borderRadius: BorderRadius.circular(r),
          border: showBorder ? Border.all(color: borderColor, width: 1) : null,
          boxShadow: isDark ? null : NeptunShadows.low,
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(r),
          child: inner,
        ),
      ),
    );
  }
}
