import 'dart:io';
import 'dart:ui';
import 'package:flutter/material.dart';

/// **NeptunGlass** — unified glassmorphism widget.
///
/// Replaces GlassContainer, RealGlassContainer, and NeptunCard.glass logic.
/// Uses theme-aware colors, skips BackdropFilter on Android for performance.
class NeptunGlass extends StatelessWidget {
  final Widget child;
  final double blur;
  final EdgeInsetsGeometry padding;
  final EdgeInsetsGeometry? margin;
  final double borderRadius;
  final Color? color;
  final Border? border;
  final VoidCallback? onTap;

  const NeptunGlass({
    super.key,
    required this.child,
    this.blur = 20.0,
    this.padding = const EdgeInsets.all(16),
    this.margin,
    this.borderRadius = 20.0,
    this.color,
    this.border,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final cs = Theme.of(context).colorScheme;

    final glassColor =
        color ??
        (isDark
            ? cs.surface.withValues(alpha: 0.7)
            : cs.surfaceContainer.withValues(alpha: 0.85));

    final glassBorder =
        border ??
        Border.all(
          color: isDark
              ? cs.outline.withValues(alpha: 0.15)
              : cs.outline.withValues(alpha: 0.2),
          width: 0.5,
        );

    final skipBlur = Platform.isAndroid;

    Widget content = ClipRRect(
      borderRadius: BorderRadius.circular(borderRadius),
      child: skipBlur
          ? Container(
              padding: padding,
              decoration: BoxDecoration(
                color: glassColor,
                borderRadius: BorderRadius.circular(borderRadius),
                border: glassBorder,
              ),
              child: child,
            )
          : BackdropFilter(
              filter: ImageFilter.blur(sigmaX: blur, sigmaY: blur),
              child: Container(
                padding: padding,
                decoration: BoxDecoration(
                  color: glassColor,
                  borderRadius: BorderRadius.circular(borderRadius),
                  border: glassBorder,
                ),
                child: child,
              ),
            ),
    );

    if (margin != null) {
      content = Padding(padding: margin!, child: content);
    }

    if (onTap != null) {
      return GestureDetector(
        onTap: onTap,
        behavior: HitTestBehavior.opaque,
        child: content,
      );
    }

    return content;
  }
}
