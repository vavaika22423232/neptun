import 'package:flutter/material.dart';

import 'neptun_glass.dart';
import 'scale_on_tap.dart';

enum NeptunCardVariant { elevated, outlined, glass }

/// Unified card component replacing glass_container, real_glass_container, glass_bento.
class NeptunCard extends StatelessWidget {
  final Widget child;
  final NeptunCardVariant variant;
  final EdgeInsetsGeometry? padding;
  final EdgeInsetsGeometry? margin;
  final double borderRadius;
  final Color? backgroundColor;
  final Color? borderColor;
  final Color? iconAccent;
  final bool showDividerBelow;
  final VoidCallback? onTap;
  final VoidCallback? onLongPress;

  const NeptunCard({
    super.key,
    required this.child,
    this.variant = NeptunCardVariant.elevated,
    this.padding,
    this.margin,
    this.borderRadius = 16,
    this.backgroundColor,
    this.borderColor,
    this.iconAccent,
    this.showDividerBelow = false,
    this.onTap,
    this.onLongPress,
  });

  const NeptunCard.outlined({
    super.key,
    required this.child,
    this.padding,
    this.margin,
    this.borderRadius = 16,
    this.backgroundColor,
    this.borderColor,
    this.iconAccent,
    this.showDividerBelow = false,
    this.onTap,
    this.onLongPress,
  }) : variant = NeptunCardVariant.outlined;

  const NeptunCard.glass({
    super.key,
    required this.child,
    this.padding,
    this.margin,
    this.borderRadius = 16,
    this.backgroundColor,
    this.borderColor,
    this.iconAccent,
    this.showDividerBelow = false,
    this.onTap,
    this.onLongPress,
  }) : variant = NeptunCardVariant.glass;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    Widget content = Padding(
      padding: padding ?? const EdgeInsets.all(16),
      child: child,
    );

    if (onTap != null || onLongPress != null) {
      content = ScaleOnTap(
        onTap: onTap,
        onLongPress: onLongPress,
        child: content,
      );
    }

    if (iconAccent != null) {
      content = IconTheme.merge(
        data: IconThemeData(color: iconAccent),
        child: content,
      );
    }

    if (showDividerBelow) {
      content = Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          content,
          Divider(
            height: 1,
            color: cs.outline.withValues(alpha: isDark ? 0.35 : 0.2),
          ),
        ],
      );
    }

    switch (variant) {
      case NeptunCardVariant.elevated:
        return Container(
          margin: margin,
          decoration: BoxDecoration(
            color: backgroundColor ?? cs.surfaceContainer,
            borderRadius: BorderRadius.circular(borderRadius),
            border: Border.all(
              color: borderColor ?? (isDark
                  ? cs.outline.withValues(alpha: 0.35)
                  : cs.outline.withValues(alpha: 0.2)),
              width: 1,
            ),
            boxShadow: isDark
                ? [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.25),
                      blurRadius: 16,
                      offset: const Offset(0, 4),
                    ),
                  ]
                : [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.05),
                      blurRadius: 16,
                      offset: const Offset(0, 4),
                    ),
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.02),
                      blurRadius: 4,
                      offset: const Offset(0, 1),
                    ),
                  ],
          ),
          clipBehavior: Clip.antiAlias,
          child: content,
        );

      case NeptunCardVariant.outlined:
        return Container(
          margin: margin,
          decoration: BoxDecoration(
            color: backgroundColor ?? Colors.transparent,
            borderRadius: BorderRadius.circular(borderRadius),
            border: Border.all(
              color: borderColor ?? cs.outline.withValues(alpha: isDark ? 0.5 : 0.4),
              width: 1,
            ),
          ),
          clipBehavior: Clip.antiAlias,
          child: content,
        );

      case NeptunCardVariant.glass:
        return NeptunGlass(
          padding: EdgeInsets.zero,
          margin: margin,
          borderRadius: borderRadius,
          color: backgroundColor,
          child: content,
        );
    }
  }
}
