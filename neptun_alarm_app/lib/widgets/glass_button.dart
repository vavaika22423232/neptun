import 'package:flutter/material.dart';

import '../design/neptun_design.dart';

enum GlassButtonVariant { primary, secondary }

/// Simple button: primary (solid fill) or secondary (outlined).
class GlassButton extends StatelessWidget {
  final VoidCallback onTap;
  final String label;
  final IconData? icon;
  final GlassButtonVariant variant;
  final double? width;
  final double height;

  const GlassButton({
    super.key,
    required this.onTap,
    required this.label,
    this.icon,
    this.variant = GlassButtonVariant.primary,
    this.width,
    this.height = 48,
  });

  const GlassButton.secondary({
    super.key,
    required this.onTap,
    required this.label,
    this.icon,
    this.width,
    this.height = 48,
  }) : variant = GlassButtonVariant.secondary;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final cs = Theme.of(context).colorScheme;

    final isPrimary = variant == GlassButtonVariant.primary;

    final bgColor = isPrimary ? cs.primary : Colors.transparent;

    final borderColor = isPrimary
        ? null
        : (isDark
              ? cs.outline.withValues(alpha: 0.5)
              : cs.outline.withValues(alpha: 0.3));

    final textColor = isPrimary ? cs.onPrimary : cs.onSurface;

    final inkChild = Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[
            Icon(icon, color: textColor, size: 18),
            const SizedBox(width: 8),
          ],
          Text(
            label,
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w600,
              color: textColor,
            ),
          ),
        ],
      ),
    );

    return Container(
      width: width,
      height: height,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(NeptunRadius.lg),
        color: bgColor,
        border: borderColor != null
            ? Border.all(color: borderColor, width: 1)
            : null,
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(NeptunRadius.lg),
          child: SizedBox(
            height: height,
            child: Center(child: inkChild),
          ),
        ),
      ),
    );
  }
}
