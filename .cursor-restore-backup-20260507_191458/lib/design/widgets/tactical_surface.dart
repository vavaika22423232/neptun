import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../neptun_design.dart';
import '../../core/widgets/scale_on_tap.dart';

/// Premium layered surface with tactical styling.
/// Replaces generic NeptunCard for dashboard-style blocks.
///
/// Variants:
/// - [TacticalSurfaceStyle.flat] - minimal, subtle border
/// - [TacticalSurfaceStyle.raised] - elevated with shadow
/// - [TacticalSurfaceStyle.glow] - accent glow (for status/alarm)
class TacticalSurface extends StatelessWidget {
  final Widget child;
  final TacticalSurfaceStyle style;
  final EdgeInsetsGeometry? padding;
  final EdgeInsetsGeometry? margin;
  final Color? accentGlow; // For glow variant
  final VoidCallback? onTap;
  final VoidCallback? onLongPress;

  const TacticalSurface({
    super.key,
    required this.child,
    this.style = TacticalSurfaceStyle.flat,
    this.padding,
    this.margin,
    this.accentGlow,
    this.onTap,
    this.onLongPress,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final cs = Theme.of(context).colorScheme;

    Color surfaceColor;
    if (isDark) {
      surfaceColor = style == TacticalSurfaceStyle.raised
          ? NeptunSurfaces.s2
          : NeptunSurfaces.s1;
    } else {
      surfaceColor = cs.surfaceContainer;
    }

    List<BoxShadow>? shadows;
    if (style == TacticalSurfaceStyle.raised && isDark) {
      shadows = [
        BoxShadow(
          color: Colors.black.withValues(alpha: 0.4),
          blurRadius: 18,
          offset: const Offset(0, 8),
        ),
      ];
    } else if (style == TacticalSurfaceStyle.glow && accentGlow != null) {
      shadows = [
        BoxShadow(
          color: accentGlow!.withValues(alpha: 0.25),
          blurRadius: 16,
          spreadRadius: 0,
          offset: const Offset(0, 2),
        ),
        BoxShadow(
          color: Colors.black.withValues(alpha: 0.3),
          blurRadius: 8,
          offset: const Offset(0, 2),
        ),
      ];
    }

    final borderColor = isDark
        ? (style == TacticalSurfaceStyle.glow && accentGlow != null
              ? accentGlow!.withValues(alpha: 0.35)
              : NeptunSurfaces.border)
        : cs.outline.withValues(alpha: 0.2);

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
      margin: margin ?? const EdgeInsets.only(bottom: NeptunSpacing.md),
      decoration: BoxDecoration(
        color: surfaceColor,
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: borderColor, width: 1),
        boxShadow: shadows,
      ),
      clipBehavior: Clip.antiAlias,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap != null
              ? () {
                  HapticFeedback.selectionClick();
                  onTap!();
                }
              : null,
          onLongPress: onLongPress,
          child: content,
        ),
      ),
    );
  }
}

enum TacticalSurfaceStyle { flat, raised, glow }
