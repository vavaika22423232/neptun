import 'package:flutter/material.dart';
import '../neptun_design.dart';
import '../../core/widgets/scale_on_tap.dart';

enum TacticalSurfaceStyle { flat, raised, glow }

/// Simple surface for dashboard blocks: flat, slightly raised, or accent glow.
class TacticalSurface extends StatelessWidget {
  final Widget child;
  final TacticalSurfaceStyle style;
  final Color? accentGlow;
  final EdgeInsetsGeometry? padding;
  final EdgeInsetsGeometry? margin;
  final VoidCallback? onTap;
  final VoidCallback? onLongPress;

  const TacticalSurface({
    super.key,
    required this.child,
    this.style = TacticalSurfaceStyle.flat,
    this.accentGlow,
    this.padding,
    this.margin,
    this.onTap,
    this.onLongPress,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final cs = Theme.of(context).colorScheme;

    final surfaceColor = isDark ? NeptunSurfaces.s1 : cs.surfaceContainer;
    final glowAccent =
        style == TacticalSurfaceStyle.glow ? accentGlow : null;
    final borderColor = glowAccent != null
        ? glowAccent.withValues(alpha: isDark ? 0.55 : 0.4)
        : (isDark
            ? NeptunSurfaces.border.withValues(alpha: 0.6)
            : cs.outline.withValues(alpha: 0.15));

    Widget content = Padding(
      padding: padding ?? NeptunSpacing.cardPadding,
      child: child,
    );

    if (onTap != null || onLongPress != null) {
      content = ScaleOnTap(
        onTap: onTap,
        onLongPress: onLongPress,
        child: content,
      );
    }

    return Container(
      margin: margin ?? const EdgeInsets.only(bottom: NeptunSpacing.xl),
      decoration: BoxDecoration(
        color: surfaceColor,
        borderRadius: BorderRadius.circular(NeptunRadius.lg),
        border: Border.all(color: borderColor, width: glowAccent != null ? 1 : 0.5),
        boxShadow: glowAccent != null
            ? [
                BoxShadow(
                  color: glowAccent.withValues(alpha: isDark ? 0.42 : 0.28),
                  blurRadius: 18,
                  spreadRadius: 0,
                  offset: const Offset(0, 6),
                ),
              ]
            : null,
      ),
      clipBehavior: Clip.antiAlias,
      child: Material(
        color: Colors.transparent,
        child: InkWell(onTap: onTap, onLongPress: onLongPress, child: content),
      ),
    );
  }
}
