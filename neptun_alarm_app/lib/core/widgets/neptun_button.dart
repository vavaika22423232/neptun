import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';

enum NeptunButtonVariant { primary, secondary, danger, ghost }

/// Unified button component with consistent styling across the app.
class NeptunButton extends StatelessWidget {
  final String label;
  final VoidCallback? onPressed;
  final NeptunButtonVariant variant;
  final IconData? icon;
  final bool isLoading;
  final bool isExpanded;
  final double? height;

  const NeptunButton({
    super.key,
    required this.label,
    this.onPressed,
    this.variant = NeptunButtonVariant.primary,
    this.icon,
    this.isLoading = false,
    this.isExpanded = false,
    this.height,
  });

  const NeptunButton.secondary({
    super.key,
    required this.label,
    this.onPressed,
    this.icon,
    this.isLoading = false,
    this.isExpanded = false,
    this.height,
  }) : variant = NeptunButtonVariant.secondary;

  const NeptunButton.danger({
    super.key,
    required this.label,
    this.onPressed,
    this.icon,
    this.isLoading = false,
    this.isExpanded = false,
    this.height,
  }) : variant = NeptunButtonVariant.danger;

  const NeptunButton.ghost({
    super.key,
    required this.label,
    this.onPressed,
    this.icon,
    this.isLoading = false,
    this.isExpanded = false,
    this.height,
  }) : variant = NeptunButtonVariant.ghost;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    Color bgColor;
    Color fgColor;
    Color borderColor;

    switch (variant) {
      case NeptunButtonVariant.primary:
        bgColor = cs.primary;
        fgColor = cs.onPrimary;
        borderColor = Colors.transparent;
        break;
      case NeptunButtonVariant.secondary:
        bgColor = isDark
            ? Colors.white.withValues(alpha: 0.08)
            : Colors.black.withValues(alpha: 0.05);
        fgColor = cs.onSurface;
        borderColor = cs.outline.withValues(alpha: 0.3);
        break;
      case NeptunButtonVariant.danger:
        bgColor = cs.error.withValues(alpha: 0.15);
        fgColor = cs.error;
        borderColor = cs.error.withValues(alpha: 0.3);
        break;
      case NeptunButtonVariant.ghost:
        bgColor = Colors.transparent;
        fgColor = cs.primary;
        borderColor = Colors.transparent;
        break;
    }

    Widget child;
    if (isLoading) {
      child = SizedBox(
        width: 20,
        height: 20,
        child: CircularProgressIndicator(strokeWidth: 2, color: fgColor),
      );
    } else {
      child = Row(
        mainAxisSize: isExpanded ? MainAxisSize.max : MainAxisSize.min,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          if (icon != null) ...[
            Icon(icon, size: 18, color: fgColor),
            const SizedBox(width: 8),
          ],
          Text(
            label,
            style: GoogleFonts.plusJakartaSans(
              fontSize: 14,
              fontWeight: FontWeight.w600,
              color: fgColor,
            ),
          ),
        ],
      );
    }

    final useGradient = variant == NeptunButtonVariant.primary;

    return SizedBox(
      width: isExpanded ? double.infinity : null,
      height: height ?? 48,
      child: Material(
        color: useGradient ? Colors.transparent : bgColor,
        borderRadius: BorderRadius.circular(12),
        child: InkWell(
          onTap: isLoading
              ? null
              : () {
                  HapticFeedback.lightImpact();
                  onPressed?.call();
                },
          borderRadius: BorderRadius.circular(12),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            decoration: BoxDecoration(
              gradient: useGradient
                  ? LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [cs.primary, cs.primary.withValues(alpha: 0.88)],
                    )
                  : null,
              color: useGradient ? null : Colors.transparent,
              borderRadius: BorderRadius.circular(12),
              border: borderColor != Colors.transparent
                  ? Border.all(color: borderColor, width: 0.5)
                  : null,
              boxShadow: useGradient && isDark
                  ? [
                      BoxShadow(
                        color: cs.primary.withValues(alpha: 0.35),
                        blurRadius: 12,
                        offset: const Offset(0, 4),
                      ),
                    ]
                  : null,
            ),
            alignment: Alignment.center,
            child: child,
          ),
        ),
      ),
    );
  }
}
